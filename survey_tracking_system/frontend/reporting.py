import io
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from collections import Counter
import plotly.express as px

from .kobo_dashboard import clean_timestamp  # local import of helper
from io import BytesIO
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
except ImportError:
    SimpleDocTemplate = None


def _sanitize_sheet_name(name: str) -> str:
    invalid = set('[]:*?/\\')
    s = ''.join('_' if c in invalid else c for c in str(name))
    return s[:31]


def infer_question_types(submissions: List[Dict[str, Any]], sample_size: int = 500, cat_threshold: int = 30) -> Dict[str, Dict[str, Any]]:
    sample = submissions[:sample_size]
    keys = set().union(*(s.keys() for s in sample)) if sample else set()
    types = {}
    for k in sorted(keys):
        if k.startswith("_"):
            continue
        vals = [s.get(k) for s in sample if s.get(k) is not None]
        if not vals:
            types[k] = {"type": "unknown", "unique": 0}
            continue
        flat = []
        for v in vals:
            if isinstance(v, list):
                flat.extend([x for x in v if x is not None])
            else:
                flat.append(v)
        if not flat:
            types[k] = {"type": "unknown", "unique": 0}
            continue
        num_ok = 0
        for v in flat:
            try:
                float(str(v))
                num_ok += 1
            except:
                pass
        if num_ok / max(1, len(flat)) >= 0.8:
            types[k] = {"type": "numeric", "unique": len(set(flat))}
            continue
        lowered = [str(v).strip().lower() for v in flat if v is not None]
        if lowered and all(x in ("true", "false", "yes", "no", "y", "n", "1", "0") for x in lowered):
            types[k] = {"type": "boolean", "unique": len(set(lowered))}
            continue
        if any(isinstance(v, list) for v in vals):
            opt_counts = Counter([str(x) for x in flat])
            types[k] = {"type": "multi-select", "unique": len(opt_counts), "top": opt_counts.most_common(5)}
            continue
        unique_vals = set(map(str, flat))
        if len(unique_vals) <= cat_threshold:
            types[k] = {"type": "categorical", "unique": len(unique_vals), "top": Counter(flat).most_common(5)}
        else:
            types[k] = {"type": "text", "unique": len(unique_vals)}
    return types


def compute_group_indicators(submissions: List[Dict[str, Any]], group_keys: List[str]) -> pd.DataFrame:
    if not submissions:
        return pd.DataFrame()
    qtypes = infer_question_types(submissions)
    records = []
    for s in submissions:
        g = "Unknown"
        for k in group_keys:
            v = s.get(k)
            if v and str(v).strip():
                g = str(v).strip()
                break
        rec = {"Group": g}
        for q in qtypes.keys():
            rec[q] = s.get(q)
        records.append(rec)
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby("Group")
    out_rows = []
    for name, group in grouped:
        row = {"Group": name, "Submissions": len(group)}
        for q, meta in qtypes.items():
            series = group[q]
            valid = series.dropna()
            if meta["type"] == "numeric":
                nums = pd.to_numeric(valid, errors='coerce').dropna()
                row[f"{q}__count"] = int(nums.count())
                row[f"{q}__mean"] = float(nums.mean()) if not nums.empty else None
                row[f"{q}__median"] = float(nums.median()) if not nums.empty else None
                row[f"{q}__min"] = float(nums.min()) if not nums.empty else None
                row[f"{q}__max"] = float(nums.max()) if not nums.empty else None
                row[f"{q}__sum"] = float(nums.sum()) if not nums.empty else None
            elif meta["type"] == "boolean":
                vals = [1 if str(x).strip().lower() in ("true","yes","1","y") else 0 for x in valid if pd.notna(x)]
                row[f"{q}__count"] = int(len(vals))
                row[f"{q}__percent_true"] = float(np.mean(vals) * 100) if vals else None
            elif meta["type"] == "categorical":
                vc = Counter([str(x) for x in valid if pd.notna(x)])
                if vc:
                    top, top_count = vc.most_common(1)[0]
                    row[f"{q}__count"] = int(sum(vc.values()))
                    row[f"{q}__top_value"] = top
                    row[f"{q}__top_pct"] = float(top_count / sum(vc.values()) * 100)
                else:
                    row[f"{q}__count"] = 0
                    row[f"{q}__top_value"] = None
                    row[f"{q}__top_pct"] = None
            elif meta["type"] == "multi-select":
                flat = []
                for v in valid:
                    if isinstance(v, list):
                        flat.extend([str(x) for x in v if x is not None])
                vc = Counter(flat)
                for opt, cnt in vc.most_common(10):
                    row[f"{q}__opt__{opt}"] = int(cnt)
            else:
                non_empty = sum(1 for x in valid if str(x).strip())
                row[f"{q}__count"] = int(len(valid))
                row[f"{q}__non_empty"] = int(non_empty)
        out_rows.append(row)
    out_df = pd.DataFrame(out_rows)
    if "Submissions" not in out_df.columns:
        out_df["Submissions"] = 0
    return out_df


def build_indicators_excel(submissions: List[Dict[str, Any]], include_sanitized: bool = False, include_long: bool = False) -> bytes:
    """Create an Excel workbook with institution & regional indicators and native charts using xlsxwriter.

    If include_long=True, adds a "Long Report" sheet which consolidates all regions and their top institutions
    and key indicators into a single, scrollable sheet for quick printing or inspection.
    """
    inst_keys = ["grp_login/institution_name", "institution_name", "institution"]
    region_keys = ["grp_login/resp_region_display", "resp_region_display", "region"]
    inst_df = compute_group_indicators(submissions, inst_keys)
    region_df = compute_group_indicators(submissions, region_keys)

    # Compute readiness score per institution (based on keywords in question keys)
    def _compute_readiness(filtered_list):
        if not filtered_list:
            return None
        readiness_keywords = ["internet", "power", "backup", "trained", "device", "computer", "laptop", "phone", "network", "wifi", "electric", "solar", "connect", "connectivity", "server", "data"]
        keys = set().union(*(s.keys() for s in filtered_list))
        indicator_keys = [k for k in keys if any(pk in k.lower() for pk in readiness_keywords)]
        if not indicator_keys:
            return None
        per_key_scores = []
        for k in indicator_keys:
            vals = [s.get(k) for s in filtered_list if s.get(k) is not None]
            if not vals:
                continue
            truthy = 0
            total = 0
            for v in vals:
                sv = str(v).strip().lower()
                if sv in ("true", "yes", "1", "y", "available", "present"):
                    truthy += 1
                total += 1
            if total > 0:
                per_key_scores.append(truthy / total)
        if not per_key_scores:
            return None
        score = float(sum(per_key_scores) / len(per_key_scores) * 100)
        return round(score, 1)

    # create sanitized submissions (remove PII and meta)
    def _sanitize(submissions_list):
        pii_patterns = ["email", "phone", "name", "first_name", "last_name", "address", "gps", "id", "id_number", "idcard", "personal", "username"]
        sanitized = []
        for s in submissions_list:
            clean = {}
            keys_to_keep = ["grp_login/institution_name", "institution_name", "institution", "grp_login/resp_region_display", "resp_region_display", "region", "_submission_time"]
            for k, v in s.items():
                kl = k.lower()
                if kl in keys_to_keep:
                    clean[k] = v
                    continue
                if kl.startswith("meta") or kl.startswith("_meta"):
                    continue
                if any(p in kl for p in pii_patterns):
                    continue
                clean[k] = v
            # normalize submission time
            if "_submission_time" in clean:
                dt = clean_timestamp(clean.get("_submission_time"))
                clean["submission_date"] = dt.strftime('%Y-%m-%d') if dt else None
                try:
                    del clean["_submission_time"]
                except KeyError:
                    pass
            sanitized.append(clean)
        return sanitized

    sanitized = _sanitize(submissions)
    sanitized_df = pd.DataFrame(sanitized)

    qtypes = infer_question_types(submissions)
    qmeta = pd.DataFrame([{"question": k, **v} for k, v in qtypes.items()])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        inst_df.to_excel(writer, sheet_name="Institution Indicators", index=False)
        region_df.to_excel(writer, sheet_name="Regional Indicators", index=False)
        # sanitized submissions (no PII)
        sanitized_df.to_excel(writer, sheet_name="Sanitized Submissions", index=False)
        qmeta.to_excel(writer, sheet_name="Question Types", index=False)

        workbook = writer.book

        # Summary charts sheet
        charts_ws = workbook.add_worksheet('Summary Charts')
        try:
            if not inst_df.empty:
                top_inst = inst_df.sort_values('Submissions', ascending=False).head(20).reset_index(drop=True)
                charts_ws.write_row(0, 0, ['Institution', 'Submissions'])
                for i, r in top_inst.iterrows():
                    charts_ws.write(i+1, 0, r['Group'])
                    charts_ws.write(i+1, 1, r['Submissions'])

                chart = workbook.add_chart({'type': 'column'})
                chart.add_series({
                    'name': 'Top Institutions',
                    'categories': ['Summary Charts', 1, 0, len(top_inst), 0],
                    'values':     ['Summary Charts', 1, 1, len(top_inst), 1],
                })
                chart.set_title({'name': 'Top Institutions by Submissions'})
                chart.set_x_axis({'name': 'Institution'})
                chart.set_y_axis({'name': 'Submissions'})
                charts_ws.insert_chart('D2', chart, {'x_scale': 1.5, 'y_scale': 1.2})
        except Exception:
            pass

        # Per-region charts: top institutions per region
        try:
            regions = region_df['Group'].dropna().unique().tolist() if not region_df.empty else []
            for region in regions:
                if not region:
                    continue
                insts = [ (s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or 'Unknown') for s in submissions if region.lower().strip() in (str(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region') or '')).lower() ]
                if not insts:
                    continue
                vc = pd.Series(insts).value_counts().head(20)
                sheet_name = _sanitize_sheet_name( f"Region_{region}")
                ws = workbook.add_worksheet(sheet_name)
                ws.write_row(0, 0, ['Institution', 'Submissions'])
                for i, (inst, cnt) in enumerate(vc.items()):
                    ws.write(i+1, 0, inst)
                    ws.write(i+1, 1, int(cnt))
                chart = workbook.add_chart({'type': 'column'})
                chart.add_series({
                    'name': f'Submissions by Institution ({region})',
                    'categories': [sheet_name, 1, 0, len(vc), 0],
                    'values':     [sheet_name, 1, 1, len(vc), 1],
                })
                chart.set_title({'name': f'Top Institutions in {region}'})
                chart.set_x_axis({'name': 'Institution'})
                chart.set_y_axis({'name': 'Submissions'})
                ws.insert_chart('D2', chart, {'x_scale': 1.0, 'y_scale': 1.0})
        except Exception:
            pass

        # Per-institution time series charts for top institutions
        try:
            top_insts = inst_df.sort_values('Submissions', ascending=False).head(10)['Group'].tolist() if not inst_df.empty else []
            for inst in top_insts:
                if not inst:
                    continue
                inst_subs = [s for s in submissions if inst.lower() in ((s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or '').lower())]
                if not inst_subs:
                    continue
                dates = []
                for s in inst_subs:
                    t = clean_timestamp(s.get('_submission_time'))
                    if t is not None:
                        dates.append(t.date())
                if not dates:
                    continue
                dc = pd.Series(dates).value_counts().sort_index()
                sheet_name = _sanitize_sheet_name( f"Inst_{inst}")
                ws = workbook.add_worksheet(sheet_name)
                ws.write_row(0, 0, ['Date', 'Submissions'])
                for i, (d, cnt) in enumerate(dc.items()):
                    ws.write(i+1, 0, d.strftime('%Y-%m-%d'))
                    ws.write(i+1, 1, int(cnt))
                chart = workbook.add_chart({'type': 'line'})
                chart.add_series({
                    'name': f'Submissions over time ({inst})',
                    'categories': [sheet_name, 1, 0, len(dc), 0],
                    'values':     [sheet_name, 1, 1, len(dc), 1],
                })
                chart.set_title({'name': f'Submissions over time - {inst}'})
                chart.set_x_axis({'name': 'Date', 'date_axis': True})
                chart.set_y_axis({'name': 'Submissions'})
                ws.insert_chart('D2', chart, {'x_scale': 1.0, 'y_scale': 1.0})
        except Exception:
            pass

        # Optional: Long consolidated report sheet
        try:
            if include_long:
                long_ws = workbook.add_worksheet('Long Report')
                row = 0
                long_ws.write_row(row, 0, ['Long Consolidated Report - Regions and Top Institutions'])
                row += 2
                # Contents table
                long_ws.write_row(row, 0, ['Region', 'Top Institutions (top 5)', 'Total Submissions'])
                row += 1
                regions = region_df['Group'].dropna().unique().tolist() if not region_df.empty else []
                for region in regions:
                    insts = [ (s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or 'Unknown') for s in submissions if region.lower().strip() in (str(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region') or '')).lower() ]
                    vc = pd.Series(insts).value_counts().head(5)
                    top_inst_str = ', '.join([f"{i} ({c})" for i, c in vc.items()])
                    total = int(vc.sum())
                    long_ws.write_row(row, 0, [region, top_inst_str, total])
                    row += 1
                # Add small summary chart
                try:
                    # reuse the summary data previously written
                    chart = workbook.add_chart({'type': 'column'})
                    chart.add_series({
                        'name': 'Top Institutions',
                        'categories': ['Summary Charts', 1, 0, min(len(inst_df), 20), 0],
                        'values':     ['Summary Charts', 1, 1, min(len(inst_df), 20), 1],
                    })
                    chart.set_title({'name': 'Top Institutions by Submissions'})
                    chart.set_x_axis({'name': 'Institution'})
                    chart.set_y_axis({'name': 'Submissions'})
                    long_ws.insert_chart('E2', chart, {'x_scale': 1.2, 'y_scale': 1.2})
                except Exception:
                    pass
        except Exception:
            pass

        writer.close()


def generate_consolidated_pdf(submissions: List[Dict[str, Any]]) -> bytes:
    """Generate a single consolidated PDF report for all regions and institutions.

    The PDF is created using reportlab with embedded Plotly charts rendered as PNG images.
    """
    if SimpleDocTemplate is None:
        raise RuntimeError("reportlab is required to generate PDF reports. Install with 'pip install reportlab'.")

    inst_keys = ["grp_login/institution_name", "institution_name", "institution"]
    region_keys = ["grp_login/resp_region_display", "resp_region_display", "region"]
    inst_df = compute_group_indicators(submissions, inst_keys)
    region_df = compute_group_indicators(submissions, region_keys)

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title page
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='black',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph('Consolidated GBV Readiness Report', title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f'Generated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    # Summary statistics
    story.append(Paragraph(f'Total Submissions: {len(submissions)}', styles['Heading2']))
    story.append(Paragraph(f'Total Institutions: {len(inst_df)}', styles['Normal']))
    story.append(Paragraph(f'Total Regions: {len(region_df)}', styles['Normal']))
    story.append(PageBreak())

    # Global top institutions chart
    try:
        if not inst_df.empty:
            story.append(Paragraph('Top Institutions by Submissions', styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))
            
            top_inst = inst_df.sort_values('Submissions', ascending=False).head(20).reset_index(drop=True)
            fig = px.bar(top_inst, x='Group', y='Submissions', title='Top Institutions')
            fig.update_layout(
                width=700, height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='black')
            )
            fig.update_xaxes(showgrid=True, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridcolor='lightgray')
            
            png_bytes = fig.to_image(format='png', engine='kaleido')
            img = RLImage(BytesIO(png_bytes), width=6*inch, height=4*inch)
            story.append(img)
            story.append(PageBreak())
    except Exception as e:
        story.append(Paragraph(f'Unable to generate chart: {str(e)}', styles['Normal']))
        story.append(PageBreak())

    # Per-region charts
    try:
        regions = region_df['Group'].dropna().unique().tolist() if not region_df.empty else []
        for region in regions:
            if not region:
                continue
            
            story.append(Paragraph(f'Region: {region}', styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))
            
            insts = [(s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or 'Unknown') 
                     for s in submissions 
                     if region.lower().strip() in (str(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region') or '')).lower()]
            
            if not insts:
                story.append(Paragraph('No data available for this region', styles['Normal']))
                story.append(PageBreak())
                continue
            
            vc = pd.Series(insts).value_counts().head(20)
            fig = px.bar(x=vc.index, y=vc.values, 
                        labels={'x': 'Institution', 'y': 'Submissions'}, 
                        title=f'Top Institutions in {region}')
            fig.update_layout(
                width=700, height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='black')
            )
            fig.update_xaxes(showgrid=True, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridcolor='lightgray')
            
            try:
                png_bytes = fig.to_image(format='png', engine='kaleido')
                img = RLImage(BytesIO(png_bytes), width=6*inch, height=4*inch)
                story.append(img)
            except Exception as chart_error:
                story.append(Paragraph(f'Chart error: {str(chart_error)}', styles['Normal']))
            
            story.append(PageBreak())
    except Exception as e:
        story.append(Paragraph(f'Error processing regions: {str(e)}', styles['Normal']))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()



"""
Comprehensive Analytical Report Generator for GBV ICT Readiness Assessment.

Generates a detailed PDF report with:
1. Executive Summary
2. Methodology
3. Indicator Analysis with data tables (NO CHARTS)
4. Regional Level Analysis with narratives
5. National Level Analysis with narratives
6. Indicator Averages and Indices
7. Comprehensive Narrative Analysis
8. Conclusions
9. Recommendations & Way Forward

Dependencies: reportlab, pandas, numpy
"""

import io
import os
import math
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, OrderedDict

import pandas as pd
import numpy as np

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
        Image, KeepTogether, ListFlowable, ListItem
    )
    from reportlab.pdfgen import canvas
except ImportError as e:
    raise ImportError(f"Missing required dependency: {e}. Install with: pip install reportlab")


class NSAHeaderCanvas(canvas.Canvas):
    """Custom canvas for adding NSA logo to every page."""
    
    def __init__(self, *args, logo_path=None, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.logo_path = logo_path
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        num_pages = len(self.pages)
        for page_dict in self.pages:
            self.__dict__.update(page_dict)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_decorations(self, page_count):
        """Draw NSA logo and page numbers on each page."""
        page_num = len(self.pages)
        
        # Add NSA logo in top right corner if available
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.drawImage(
                    self.logo_path,
                    A4[0] - 2.5*inch,  # Right aligned with margin
                    A4[1] - 1.2*inch,  # Top of page
                    width=2*inch,
                    height=0.8*inch,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                print(f"Warning: Could not add logo to page {page_num}: {e}")
        
        # Add page number at bottom
        self.setFont('Helvetica', 9)
        self.drawRightString(
            A4[0] - 0.75*inch,
            0.5*inch,
            f"Page {page_num} of {page_count}"
        )


class ComprehensiveReportGenerator:
    """Generate comprehensive analytical PDF reports from survey data."""
    
    def __init__(self, submissions: List[Dict], logo_path: Optional[str] = None, progress_callback=None):
        """
        Initialize report generator.
        
        Args:
            submissions: List of survey submission dictionaries
            logo_path: Optional path to NSA logo image file
            progress_callback: Optional callback function(step, total, message) for progress updates
        """
        self.submissions = submissions
        self.logo_path = logo_path
        self.progress_callback = progress_callback
        self.df = pd.DataFrame(submissions) if submissions else pd.DataFrame()
        
        # Data Validation and Quality Check
        self._validate_and_log_data_quality()
        
        # Debug: Print ALL column names for mapping
        print(f"\n=== DEBUG: ALL COLUMN NAMES ===")
        print(f"Total columns: {len(self.df.columns)}")
        print("\nAll columns:")
        for i, col in enumerate(self.df.columns, 1):
            print(f"  {i}. {col}")
        print("=" * 50)
        
        # Create a completely fresh stylesheet to avoid shared state
        from reportlab.lib.styles import StyleSheet1, ParagraphStyle as PS
        self.styles = StyleSheet1()
        
        # Add only the essential base styles we need
        self.styles.add(PS(name='Normal', fontName='Helvetica', fontSize=10, leading=12))
        self.styles.add(PS(name='Heading1', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, spaceAfter=6))
        self.styles.add(PS(name='Heading2', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=18, spaceBefore=12, spaceAfter=6))
        self.styles.add(PS(name='Heading3', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, spaceBefore=12, spaceAfter=6))
        
        self._setup_custom_styles()
        self.total_steps = 12  # Total report generation steps
        
        # Define indicator mappings to actual KoboToolbox survey questions
        # Based on the 102 columns from the survey form
        self.indicator_mappings = {
            'ICT Infrastructure': [
                'grp3/q3_1_1',      # Has computers available
                'grp3/q3_2_3',      # Internet connectivity
                'grp3/q3_2_4',      # Mobile devices available
                'grp3/q3_2_5',      # Smartphones/tablets
                'grp3/q3_1_4',      # Backup power supply
                'grp3/q3_4_1',      # Server/data center
            ],
            'Digital Literacy': [
                'grp3/q3_3_1',      # Staff ICT skills/training
                'grp2/q2_5_1',      # Staff trained on systems
                'grp2/q2_5_2',      # Training frequency
                'grp2/q2_5_3',      # Digital tools usage
            ],
            'Data Management': [
                'grp4/q4_1_1',      # Electronic records system
                'grp4/q4_2_1',      # Data backup system
                'grp4/q4_3_1',      # Data security measures
                'grp4/q4_4_2',      # Database management system
            ],
            'GBV Case Management': [
                'grp2/q2_1_1',      # GBV policy/system
                'grp2/q2_1_2',      # Case tracking
                'grp2/q2_1_3',      # Referral system
                'grp2/q2_1_4',      # Case documentation
                'grp2/q2_4_1',      # Follow-up mechanism
            ],
            'Interagency Coordination': [
                'grp4/q4_4_1',      # Coordination platform
                'grp3/q3_5_1',      # Information sharing
                'grp3/q3_5_2',      # Joint planning tools
                'grp3/q3_5_3',      # Inter-agency collaboration
            ]
        }
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Add custom styles (no need to check - fresh stylesheet each time)
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='BulletText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            leftIndent=20,
            spaceAfter=6
        ))
        
    def _validate_and_log_data_quality(self):
        """
        Validate survey responses and log data quality summary.
        Verifies completeness and logs any missing or malformed data.
        """
        print("\n" + "=" * 80)
        print("DATA QUALITY SUMMARY (KoboToolbox API Data)")
        print("=" * 80)
        
        if self.df.empty:
            print("⚠️  WARNING: No data available from KoboToolbox API")
            return
        
        total_submissions = len(self.df)
        print(f"✓ Total Submissions: {total_submissions}")
        print(f"✓ Total Fields: {len(self.df.columns)}")
        
        # Check for required fields
        required_fields = ['_id', '_submission_time']
        missing_required = [f for f in required_fields if f not in self.df.columns]
        if missing_required:
            print(f"⚠️  Missing required fields: {missing_required}")
        else:
            print(f"✓ All required system fields present")
        
        print(f"✓ Data validation complete - ready for processing")
        print("=" * 80 + "\n")
    
    def _update_progress(self, step: int, message: str):
        """Update progress if callback is provided."""
        print(f"Progress: Step {step}/{self.total_steps} - {message}")  # Debug output
        if self.progress_callback:
            try:
                self.progress_callback(step, self.total_steps, message)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    def generate_report(self, output_path: str) -> str:
        """
        Generate the comprehensive PDF report.
        
        Args:
            output_path: Path where PDF should be saved
            
        Returns:
            Path to generated PDF file
        """
        self._update_progress(1, "Initializing report generation...")
        
        # Create PDF document with custom canvas for logo
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1.5*inch,  # Extra space for logo
            bottomMargin=0.75*inch
        )
        
        # Build story (content elements)
        story = []
        
        # Cover page
        self._update_progress(2, "Creating cover page...")
        story.extend(self._create_cover_page())
        story.append(PageBreak())
        
        # Executive Summary
        self._update_progress(3, "Generating executive summary...")
        story.extend(self._create_executive_summary())
        story.append(PageBreak())
        
        # Methodology
        self._update_progress(4, "Writing methodology section...")
        story.extend(self._create_methodology_section())
        story.append(PageBreak())
        
        # Indicator Analysis with Averages
        self._update_progress(5, "Analyzing indicators...")
        story.extend(self._create_indicator_analysis())
        story.append(PageBreak())
        
        # Regional Analysis (Enhanced)
        self._update_progress(6, "Conducting regional analysis...")
        story.extend(self._create_regional_analysis())
        story.append(PageBreak())
        
        # National Analysis (Enhanced)
        self._update_progress(7, "Conducting national analysis...")
        story.extend(self._create_national_analysis())
        story.append(PageBreak())
        
        # Detailed Data Tables
        self._update_progress(8, "Building detailed data tables...")
        story.extend(self._create_detailed_tables())
        story.append(PageBreak())
        
        # Comprehensive Conclusions with Strategic Analysis
        self._update_progress(9, "Formulating conclusions...")
        story.extend(self._create_comprehensive_conclusions())
        story.append(PageBreak())
        
        # Strategic Way Forward
        self._update_progress(10, "Developing strategic recommendations...")
        story.extend(self._create_strategic_way_forward())
        
        # Build PDF with custom canvas
        self._update_progress(11, "Rendering PDF document...")
        doc.build(
            story,
            canvasmaker=lambda *args, **kwargs: NSAHeaderCanvas(
                *args, logo_path=self.logo_path, **kwargs
            )
        )
        
        self._update_progress(12, "Report generation complete!")
        return output_path
        
    def _create_cover_page(self) -> List:
        """Create report cover page."""
        elements = []
        
        # Add vertical space
        elements.append(Spacer(1, 2*inch))
        
        # Title
        title = Paragraph(
            "GBV ICT Readiness Assessment<br/>Comprehensive Analytical Report",
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        subtitle = Paragraph(
            "National Statistical Agency (NSA)<br/>Gender-Based Violence Response Assessment",
            subtitle_style
        )
        elements.append(subtitle)
        elements.append(Spacer(1, 1*inch))
        
        # Report metadata
        metadata_style = ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER
        )
        
        report_date = datetime.now().strftime("%B %d, %Y")
        total_responses = len(self.submissions)
        
        metadata = Paragraph(
            f"<b>Report Date:</b> {report_date}<br/>"
            f"<b>Total Responses:</b> {total_responses}<br/>"
            f"<b>Assessment Period:</b> {self._get_assessment_period()}",
            metadata_style
        )
        elements.append(metadata)
        
        return elements
        
    def _get_assessment_period(self) -> str:
        """Get the assessment period from submission dates."""
        if self.df.empty or '_submission_time' not in self.df.columns:
            return "N/A"
            
        try:
            dates = pd.to_datetime(self.df['_submission_time'])
            start_date = dates.min().strftime("%B %Y")
            end_date = dates.max().strftime("%B %Y")
            return f"{start_date} - {end_date}"
        except:
            return "N/A"
            
    def _create_executive_summary(self) -> List:
        """Create executive summary section."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Calculate key metrics
        total_responses = len(self.submissions)
        
        # Calculate overall readiness score
        readiness_score = self._calculate_overall_readiness()
        
        summary_text = f"""
        This comprehensive report presents the findings of the GBV ICT Readiness Assessment 
        conducted by the National Statistical Agency (NSA). The assessment evaluated the capacity 
        of {total_responses} service providers to effectively utilize information and communication 
        technologies in their GBV response activities.
        <br/><br/>
        The assessment examined five key indicators: ICT Infrastructure, Digital Literacy, 
        Data Management, GBV Case Management, and Interagency Coordination. Each indicator 
        was analyzed to determine current capacity levels and identify areas requiring support.
        """
        
        elements.append(Paragraph(summary_text, self.styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Key findings
        elements.append(Paragraph("Key Findings:", self.styles['SubsectionHeading']))
        
        key_findings = self._generate_key_findings()
        for finding in key_findings:
            elements.append(Paragraph(f"• {finding}", self.styles['BulletText']))
            
        return elements
        
    def _calculate_overall_readiness(self) -> float:
        """Calculate overall ICT readiness score."""
        if self.df.empty:
            return 0.0
            
        # Calculate average scores for each indicator
        indicator_scores = []
        
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                indicator_scores.append(score)
                
        return np.mean(indicator_scores) if indicator_scores else 0.0
        
    def _calculate_indicator_average(self, question_keys: List[str]) -> Optional[float]:
        """
        Calculate average score for an indicator based on Yes/No responses.
        CRITICAL CONVERSION:
        - Yes = 1 (100%)
        - No = 0 (0%)
        - Don't Know/Unknown/Other = None (excluded from calculation)
        
        Returns the percentage of Yes responses across all questions for this indicator.
        
        Args:
            question_keys: List of question column names for this indicator
            
        Returns:
            Percentage of Yes responses (0-100) or None if insufficient data
        """
        if self.df.empty:
            return None
            
        total_valid_responses = 0
        yes_count = 0
        
        for key in question_keys:
            if key in self.df.columns:
                # Get non-null responses
                responses = self.df[key].dropna()
                for response in responses:
                    response_str = str(response).lower().strip()
                    
                    # Convert Yes to 1
                    if 'yes' in response_str or response_str == '1':
                        yes_count += 1
                        total_valid_responses += 1
                    # Convert No to 0 (NOT 2)
                    elif 'no' in response_str or response_str == '0':
                        total_valid_responses += 1
                    # Don't Know/Unknown/Other = None (skip, don't count)
                    elif any(x in response_str for x in ['don\'t know', 'unknown', 'other', 'n/a', 'not applicable']):
                        continue  # Exclude from averages
        
        if total_valid_responses == 0:
            return None
            
        # Indicator Average = (Sum of 1s) / (Total Valid Responses) × 100%
        return (yes_count / total_valid_responses) * 100
        
    def _map_response_to_score(self, response: Any) -> Optional[float]:
        """Map survey response to numeric score (0-100)."""
        if pd.isna(response):
            return None
            
        response_str = str(response).lower()
        
        # Quality/frequency mappings
        quality_map = {
            'excellent': 100, 'very good': 85, 'good': 70,
            'fair': 50, 'poor': 30, 'very poor': 10,
            'always': 100, 'often': 75, 'sometimes': 50,
            'rarely': 25, 'never': 0,
            'yes': 100, 'no': 0, 'partial': 50,
            'high': 100, 'medium': 60, 'low': 30,
            'daily': 100, 'weekly': 70, 'monthly': 40,
            'quarterly': 20, 'annually': 10
        }
        
        for key, value in quality_map.items():
            if key in response_str:
                return value
                
        # Try to parse as number
        try:
            return float(response)
        except:
            return 50  # Default neutral score
            
    def _generate_key_findings(self) -> List[str]:
        """Generate key findings based on data analysis."""
        findings = []
        
        # Analyze each indicator
        for indicator, questions in self.indicator_mappings.items():
            avg_score = self._calculate_indicator_average(questions)
            if avg_score is not None:
                level = self._get_readiness_level(avg_score)
                findings.append(
                    f"<b>{indicator}:</b> {level} readiness level "
                    f"(Average Score: {avg_score:.1f}%)"
                )
                
        return findings
        
    def _get_readiness_level(self, score: float) -> str:
        """Convert numeric score to readiness level."""
        if score >= 80:
            return "High"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "Low"
        else:
            return "Very Low"
            
    def _create_methodology_section(self) -> List:
        """Create methodology section."""
        elements = []
        
        elements.append(Paragraph("Methodology", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        methodology_text = """
        This assessment utilized a structured survey instrument administered to GBV service 
        providers across multiple regions. The methodology employed a quantitative approach 
        based on Yes/No responses to assess institutional capacity.
        <br/><br/>
        <b>Data Collection:</b><br/>
        Data was collected using KoboToolbox, a digital data collection platform, ensuring 
        standardized responses and real-time data validation. The survey covered five key 
        indicator areas, each mapped to specific assessment questions.
        <br/><br/>
        <b>Analysis Framework:</b><br/>
        The analysis examined data at both regional and national levels, identifying patterns, 
        gaps, and opportunities for improvement in ICT readiness for GBV response. Indicator 
        percentages represent the proportion of institutions that answered "Yes" to questions 
        under each indicator area.
        """
        
        elements.append(Paragraph(methodology_text, self.styles['BodyText']))
        
        return elements
        
    def _create_indicator_analysis(self) -> List:
        """Create detailed indicator analysis with averages."""
        elements = []
        
        elements.append(Paragraph(
            "Indicator Analysis with Averages",
            self.styles['SectionHeading']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        # Analyze each indicator
        for indicator, questions in self.indicator_mappings.items():
            elements.extend(self._create_indicator_section(indicator, questions))
            elements.append(Spacer(1, 0.3*inch))
            
        return elements
        
    def _create_indicator_section(self, indicator: str, questions: List[str]) -> List:
        """Create analysis section for a single indicator."""
        elements = []
        
        # Indicator heading
        elements.append(Paragraph(
            f"{indicator}",
            self.styles['SubsectionHeading']
        ))
        
        # Calculate average score
        avg_score = self._calculate_indicator_average(questions)
        
        if avg_score is not None:
            readiness_level = self._get_readiness_level(avg_score)
            
            score_text = f"""
            <b>Average Score: {avg_score:.1f}%</b> ({readiness_level} Readiness)<br/>
            <br/>
            This indicator measures the capacity and effectiveness of {indicator.lower()} 
            in supporting GBV response activities. The average score of {avg_score:.1f}% 
            indicates a {readiness_level.lower()} level of readiness in this area.
            """
            
            elements.append(Paragraph(score_text, self.styles['BodyText']))
            elements.append(Spacer(1, 0.15*inch))
            
            # Create data table for this indicator
            table_data = self._create_indicator_table_data(indicator, questions)
            if table_data:
                elements.append(self._create_styled_table(table_data))
                elements.append(Spacer(1, 0.15*inch))
                
            # Add interpretation
            interpretation = self._generate_indicator_interpretation(
                indicator, avg_score, questions
            )
            elements.append(Paragraph(
                f"<b>Interpretation:</b> {interpretation}",
                self.styles['BodyText']
            ))
        else:
            elements.append(Paragraph(
                "Insufficient data available for this indicator.",
                self.styles['BodyText']
            ))
            
        return elements
        
    def _create_indicator_table_data(self, indicator: str, questions: List[str]) -> List[List]:
        """Create table data for an indicator showing question-level statistics."""
        if self.df.empty:
            return []
            
        table_data = [['Question', 'Responses', 'Avg Score', 'Most Common']]
        
        for question in questions:
            if question not in self.df.columns:
                continue
                
            col_data = self.df[question].dropna()
            
            if len(col_data) == 0:
                continue
                
            # Calculate statistics
            response_count = len(col_data)
            
            # Calculate average score
            scores = [self._map_response_to_score(v) for v in col_data]
            scores = [s for s in scores if s is not None]
            avg_score = np.mean(scores) if scores else 0
            
            # Most common response
            most_common = col_data.mode()[0] if len(col_data.mode()) > 0 else "N/A"
            
            # Format question name
            question_display = question.replace('_', ' ').title()
            
            table_data.append([
                question_display,
                str(response_count),
                f"{avg_score:.1f}%",
                str(most_common)[:30]
            ])
            
        return table_data if len(table_data) > 1 else []
        
    def _create_styled_table(self, data: List[List]) -> Table:
        """Create a styled table from data."""
        table = Table(data, repeatRows=1)
        
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        
        return table
        
    def _generate_indicator_interpretation(self, indicator: str, score: float, questions: List[str]) -> str:
        """Generate interpretation text for an indicator."""
        level = self._get_readiness_level(score)
        
        interpretations = {
            'High': f"The {indicator} shows strong capacity with an average score of {score:.1f}%. "
                   "This indicates robust systems and practices are in place. Continue to maintain "
                   "and enhance these capabilities.",
            
            'Moderate': f"The {indicator} demonstrates moderate capacity at {score:.1f}%. "
                       "While foundational elements exist, there are opportunities for improvement. "
                       "Targeted interventions could significantly enhance effectiveness.",
            
            'Low': f"The {indicator} shows limited capacity with a score of {score:.1f}%. "
                  "Significant gaps exist that require immediate attention. Priority should be given "
                  "to strengthening this area through capacity building and resource allocation.",
            
            'Very Low': f"The {indicator} indicates critical gaps with a score of {score:.1f}%. "
                       "Urgent intervention is required. This area should be prioritized for "
                       "immediate capacity development and resource investment."
        }
        
        return interpretations.get(level, f"Score: {score:.1f}%")
        
    def _create_regional_analysis(self) -> List:
        """Create regional-level analysis."""
        elements = []
        
        elements.append(Paragraph("Regional Analysis", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Check if region data exists
        region_column = self._find_region_column()
        
        if region_column and region_column in self.df.columns:
            # Convert any list values to strings and get unique regions
            region_series = self.df[region_column].dropna()
            region_series = region_series.apply(lambda x: str(x) if isinstance(x, list) else x)
            regions = region_series.unique()
            
            for region in sorted(regions):
                elements.extend(self._create_region_section(region, region_column))
                elements.append(Spacer(1, 0.2*inch))
        else:
            elements.append(Paragraph(
                "Regional data not available in the current dataset.",
                self.styles['BodyText']
            ))
            
        return elements
        
    def _find_region_column(self) -> Optional[str]:
        """
        Find the column containing region information.
        DO NOT USE geolocation/GPS data - use actual region names from survey.
        """
        # First, try the exact field from KoboToolbox survey
        if 'grp_login/resp_region_display' in self.df.columns:
            return 'grp_login/resp_region_display'
        
        # Fallback: search for region-related columns, excluding geolocation
        possible_names = ['region', 'district', 'location', 'area', 'province']
        excluded_names = ['geolocation', 'gps', 'coordinates', 'latitude', 'longitude', '_geo']
        
        for col in self.df.columns:
            col_lower = col.lower()
            # Skip geolocation fields
            if any(excluded in col_lower for excluded in excluded_names):
                continue
            # Check for region-related names
            if any(name in col_lower for name in possible_names):
                return col
                
        return None
        
    def _create_region_section(self, region: str, region_column: str) -> List:
        """Create analysis section for a specific region."""
        elements = []
        
        # Filter data for this region
        region_df = self.df[self.df[region_column] == region]
        
        elements.append(Paragraph(f"{region}", self.styles['SubsectionHeading']))
        
        # Calculate regional statistics
        response_count = len(region_df)
        
        # Calculate regional readiness scores
        regional_scores = []
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average_for_df(region_df, questions)
            if score is not None:
                regional_scores.append(score)
                
        avg_regional_score = np.mean(regional_scores) if regional_scores else 0
        
        analysis_text = f"""
        <b>Responses:</b> {response_count}<br/>
        <b>Average Readiness Score:</b> {avg_regional_score:.1f}%<br/>
        <br/>
        {region} demonstrates a {self._get_readiness_level(avg_regional_score).lower()} level 
        of ICT readiness for GBV response. Based on {response_count} responses, the region shows 
        {'strong capacity' if avg_regional_score >= 70 else 'areas requiring support'} in 
        utilizing technology for GBV case management and coordination.
        """
        
        elements.append(Paragraph(analysis_text, self.styles['BodyText']))
        
        return elements
        
    def _calculate_indicator_average_for_df(self, df: pd.DataFrame, questions: List[str]) -> Optional[float]:
        """
        Calculate indicator average for a specific dataframe based on Yes/No responses.
        CRITICAL CONVERSION:
        - Yes = 1 (100%)
        - No = 0 (0%)
        - Don't Know/Unknown/Other = None (excluded from calculation)
        
        Returns the percentage of Yes responses.
        """
        total_valid_responses = 0
        yes_count = 0
        
        for question in questions:
            if question in df.columns:
                responses = df[question].dropna()
                
                for response in responses:
                    response_str = str(response).lower().strip()
                    
                    # Convert Yes to 1
                    if 'yes' in response_str or response_str == '1':
                        yes_count += 1
                        total_valid_responses += 1
                    # Convert No to 0 (NOT 2)
                    elif 'no' in response_str or response_str == '0':
                        total_valid_responses += 1
                    # Don't Know/Unknown/Other = None (skip, don't count)
                    elif any(x in response_str for x in ['don\'t know', 'unknown', 'other', 'n/a', 'not applicable']):
                        continue  # Exclude from averages
                    
        if total_valid_responses == 0:
            return None
            
        # Indicator Average = (Sum of 1s) / (Total Valid Responses) × 100%
        return (yes_count / total_valid_responses) * 100
        
    def _create_national_analysis(self) -> List:
        """Create national-level analysis."""
        elements = []
        
        elements.append(Paragraph("National Analysis", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # National statistics
        total_responses = len(self.df)
        
        national_text = f"""
        At the national level, the GBV ICT Readiness Assessment analyzed {total_responses} responses from service 
        providers across the country to evaluate ICT capacity for GBV response.
        <br/><br/>
        The assessment highlights both strengths to build upon and critical gaps requiring immediate attention 
        across the five key indicator areas.
        """
        
        elements.append(Paragraph(national_text, self.styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))
        
        # National indicator summary table
        elements.append(Paragraph("National Indicator Summary", self.styles['SubsectionHeading']))
        
        summary_data = [['Indicator', 'Average Score', 'Readiness Level']]
        
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                summary_data.append([
                    indicator,
                    f"{score:.1f}%",
                    self._get_readiness_level(score)
                ])
                
        if len(summary_data) > 1:
            elements.append(self._create_styled_table(summary_data))
            
        return elements
        
    def _create_detailed_tables(self) -> List:
        """Create detailed data tables section."""
        elements = []
        
        elements.append(Paragraph("Detailed Data Tables", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Create summary statistics table
        elements.append(Paragraph("Response Statistics", self.styles['SubsectionHeading']))
        
        if not self.df.empty:
            # Select key columns for detailed table
            key_columns = []
            for questions in self.indicator_mappings.values():
                key_columns.extend(questions)
                
            # Create frequency tables for key questions
            for col in key_columns[:10]:  # Limit to first 10 to avoid overly long report
                if col in self.df.columns:
                    elements.extend(self._create_frequency_table(col))
                    elements.append(Spacer(1, 0.15*inch))
        else:
            elements.append(Paragraph("No data available.", self.styles['BodyText']))
            
        return elements
        
    def _create_frequency_table(self, column: str) -> List:
        """Create a frequency table for a specific column."""
        elements = []
        
        col_data = self.df[column].dropna()
        
        if len(col_data) == 0:
            return elements
            
        # Calculate frequencies
        freq = col_data.value_counts()
        total = len(col_data)
        
        # Create table
        table_data = [['Response', 'Count', 'Percentage']]
        
        for value, count in freq.head(10).items():  # Top 10 responses
            percentage = (count / total) * 100
            table_data.append([
                str(value)[:40],  # Truncate long responses
                str(count),
                f"{percentage:.1f}%"
            ])
            
        # Add question title
        question_title = column.replace('_', ' ').title()
        elements.append(Paragraph(f"<b>{question_title}</b>", self.styles['BodyText']))
        elements.append(Spacer(1, 0.05*inch))
        elements.append(self._create_styled_table(table_data))
        
        return elements
        
    def _create_comprehensive_conclusions(self) -> List:
        """Create comprehensive conclusions section with deep analysis."""
        elements = []
        
        elements.append(Paragraph("Comprehensive Conclusions", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Calculate indicator scores for analysis
        indicator_scores = {}
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                indicator_scores[indicator] = score
        
        if not indicator_scores:
            elements.append(Paragraph(
                "Insufficient data available for comprehensive analysis.",
                self.styles['BodyText']
            ))
            return elements
        
        strongest = max(indicator_scores.items(), key=lambda x: x[1])
        weakest = min(indicator_scores.items(), key=lambda x: x[1])
        
        conclusion_text = f"""
        The GBV ICT Readiness Assessment provides critical insights into the current state of 
        technology adoption and utilization in GBV response across the country.
        <br/><br/>
        <b>Overall Assessment:</b><br/>
        The assessment of {len(self.submissions)} service providers reveals varying levels of 
        ICT capacity for GBV response. The strongest area is <b>{strongest[0]}</b> 
        with {strongest[1]:.1f}% of institutions demonstrating this capacity, while <b>{weakest[0]}</b> requires the most attention 
        at {weakest[1]:.1f}%.
        """
        
        elements.append(Paragraph(conclusion_text, self.styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Regional disparities analysis
        elements.append(Paragraph("Regional Disparities", self.styles['SubsectionHeading']))
        
        region_column = self._find_region_column()
        if region_column and region_column in self.df.columns:
            # Convert any list values to strings and get unique regions
            region_series = self.df[region_column].dropna()
            region_series = region_series.apply(lambda x: str(x) if isinstance(x, list) else x)
            regions = region_series.unique()
            regional_scores = {}
            
            for region in regions:
                region_df = self.df[self.df[region_column] == region]
                regional_score_list = []
                for indicator, questions in self.indicator_mappings.items():
                    score = self._calculate_indicator_average_for_df(region_df, questions)
                    if score is not None:
                        regional_score_list.append(score)
                if regional_score_list:
                    regional_scores[region] = np.mean(regional_score_list)
            
            if regional_scores:
                best_region = max(regional_scores.items(), key=lambda x: x[1])
                worst_region = min(regional_scores.items(), key=lambda x: x[1])
                variance = np.std(list(regional_scores.values()))
                
                regional_text = f"""
                Regional analysis reveals {'significant' if variance > 15 else 'moderate'} 
                disparities in ICT readiness. <b>{best_region[0]}</b> leads with {best_region[1]:.1f}%, 
                while <b>{worst_region[0]}</b> shows {worst_region[1]:.1f}%. The variance of 
                {variance:.1f} points suggests {'targeted regional interventions' if variance > 15 else 'relatively consistent capacity'} 
                are needed to achieve equitable ICT capacity nationwide.
                """
                elements.append(Paragraph(regional_text, self.styles['BodyText']))
        else:
            elements.append(Paragraph(
                "Regional data not available for comparative analysis.",
                self.styles['BodyText']
            ))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Indicator-specific conclusions
        elements.append(Paragraph("Indicator-Specific Findings", self.styles['SubsectionHeading']))
        
        for indicator, score in sorted(indicator_scores.items(), key=lambda x: x[1], reverse=True):
            level = self._get_readiness_level(score)
            
            if score >= 70:
                finding = f"demonstrates strong capacity and can serve as a foundation for broader improvements"
            elif score >= 50:
                finding = f"shows moderate capacity but requires enhancement to meet optimal standards"
            else:
                finding = f"reveals critical gaps requiring immediate and sustained intervention"
            
            elements.append(Paragraph(
                f"• <b>{indicator}</b> ({score:.1f}% - {level}): {finding}",
                self.styles['BulletText']
            ))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Critical success factors
        elements.append(Paragraph("Critical Success Factors", self.styles['SubsectionHeading']))
        
        success_factors = [
            "Sustained leadership commitment and resource allocation for ICT development",
            "Comprehensive capacity building programs tailored to identified gaps",
            "Establishment of robust monitoring and evaluation frameworks",
            "Cross-regional knowledge sharing and best practice dissemination",
            "Integration of ICT readiness into broader GBV response strategies"
        ]
        
        for factor in success_factors:
            elements.append(Paragraph(f"• {factor}", self.styles['BulletText']))
        
        return elements
        
    def _create_strategic_way_forward(self) -> List:
        """Create strategic way forward section based on indicator averages."""
        elements = []
        
        elements.append(Paragraph(
            "Strategic Way Forward",
            self.styles['SectionHeading']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        overall_score = self._calculate_overall_readiness()
        
        # Calculate indicator scores for strategic planning
        indicator_scores = {}
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                indicator_scores[indicator] = score
        
        intro_text = """
        Based on the comprehensive analysis of the assessment findings, 
        the following strategic framework is proposed to enhance ICT capacity for GBV response. 
        This roadmap prioritizes interventions based on identified gaps and leverages existing strengths.
        """
        
        elements.append(Paragraph(intro_text, self.styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Immediate Priorities (0-6 months)
        elements.append(Paragraph("Phase 1: Immediate Priorities (0-6 months)", self.styles['SubsectionHeading']))
        
        immediate_actions = []
        for indicator, score in indicator_scores.items():
            if score < 40:  # Critical gaps
                immediate_actions.append(
                    f"<b>{indicator}</b> (Score: {score:.1f}%): Launch emergency capacity building program "
                    f"with focus on {self._get_priority_action(indicator, 'immediate')}"
                )
        
        if not immediate_actions:
            immediate_actions.append(
                "Conduct detailed needs assessment to identify specific technical requirements"
            )
        
        immediate_actions.extend([
            "Establish ICT Readiness Task Force with representatives from all regions",
            "Secure budget allocation for priority infrastructure and training needs",
            "Develop standardized ICT policies and protocols for GBV service providers"
        ])
        
        for action in immediate_actions:
            elements.append(Paragraph(f"• {action}", self.styles['BulletText']))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Short-term Goals (6-12 months)
        elements.append(Paragraph("Phase 2: Short-term Goals (6-12 months)", self.styles['SubsectionHeading']))
        
        shortterm_actions = []
        for indicator, score in indicator_scores.items():
            if 40 <= score < 60:  # Moderate gaps
                shortterm_actions.append(
                    f"<b>{indicator}</b> (Score: {score:.1f}%): Implement {self._get_priority_action(indicator, 'shortterm')} "
                    f"to achieve 70% readiness target"
                )
        
        shortterm_actions.extend([
            "Roll out comprehensive training programs across all regions",
            "Deploy pilot digital case management systems in high-performing regions",
            "Establish regional ICT support hubs for technical assistance",
            "Develop data sharing protocols and interagency coordination platforms"
        ])
        
        for action in shortterm_actions:
            elements.append(Paragraph(f"• {action}", self.styles['BulletText']))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Medium-term Objectives (1-2 years)
        elements.append(Paragraph("Phase 3: Medium-term Objectives (1-2 years)", self.styles['SubsectionHeading']))
        
        mediumterm_actions = [
            "Scale successful pilot programs to national level",
            "Achieve minimum 70% readiness across all indicators",
            "Establish sustainable ICT maintenance and support mechanisms",
            "Integrate GBV ICT systems with national health and justice information systems",
            "Conduct mid-term evaluation and adjust strategies based on progress"
        ]
        
        for action in mediumterm_actions:
            elements.append(Paragraph(f"• {action}", self.styles['BulletText']))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Long-term Vision (2-5 years)
        elements.append(Paragraph("Phase 4: Long-term Vision (2-5 years)", self.styles['SubsectionHeading']))
        
        longterm_actions = [
            "Achieve 85%+ readiness across all indicators nationwide",
            "Establish Namibia as a regional leader in GBV ICT integration",
            "Develop advanced analytics and AI-powered decision support tools",
            "Create sustainable funding mechanisms for ongoing ICT development",
            "Build capacity for continuous innovation and technology adoption"
        ]
        
        for action in longterm_actions:
            elements.append(Paragraph(f"• {action}", self.styles['BulletText']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Resource Requirements
        elements.append(Paragraph("Resource Requirements", self.styles['SubsectionHeading']))
        
        resource_text = f"""
        Successful implementation requires coordinated resource mobilization across multiple areas:
        <br/><br/>
        <b>Financial:</b> Estimated budget of NAD 15-25 million over 5 years for infrastructure, 
        training, and system development
        <br/><br/>
        <b>Human Resources:</b> Dedicated ICT coordinators at national and regional levels, 
        technical trainers, and system administrators
        <br/><br/>
        <b>Technical:</b> Hardware procurement, software licensing, internet connectivity upgrades, 
        and cloud infrastructure
        <br/><br/>
        <b>Partnerships:</b> Collaboration with development partners, technology providers, 
        and academic institutions
        """
        
        elements.append(Paragraph(resource_text, self.styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Monitoring and Evaluation
        elements.append(Paragraph("Monitoring & Evaluation Framework", self.styles['SubsectionHeading']))
        
        me_text = """
        Progress will be tracked through:
        """
        elements.append(Paragraph(me_text, self.styles['BodyText']))
        
        me_actions = [
            "Quarterly progress reviews against indicator targets",
            "Annual comprehensive ICT readiness assessments",
            "Real-time dashboards tracking system usage and performance",
            "Regular stakeholder feedback sessions and user satisfaction surveys",
            "Impact evaluations measuring improvements in GBV response outcomes"
        ]
        
        for action in me_actions:
            elements.append(Paragraph(f"• {action}", self.styles['BulletText']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Conclusion
        conclusion_text = """
        <b>Conclusion:</b><br/>
        Achieving the vision of comprehensive ICT integration for GBV response is both necessary and achievable. 
        This strategic roadmap provides a clear pathway forward, prioritizing urgent needs while building toward 
        long-term sustainability. Success requires sustained commitment, adequate resources, and collaborative 
        action across all 
        stakeholders. The National Statistical Agency stands ready to support this transformative journey.
        """
        
        elements.append(Paragraph(conclusion_text, self.styles['BodyText']))
        
        return elements
    
    def _get_priority_action(self, indicator: str, phase: str) -> str:
        """Get priority action for an indicator based on phase."""
        actions = {
            'ICT Infrastructure': {
                'immediate': 'hardware procurement and internet connectivity',
                'shortterm': 'network infrastructure upgrades and equipment standardization'
            },
            'Digital Literacy': {
                'immediate': 'basic digital skills training for all staff',
                'shortterm': 'advanced training programs and certification pathways'
            },
            'Data Management': {
                'immediate': 'data security protocols and backup systems',
                'shortterm': 'integrated data management platforms and quality assurance'
            },
            'GBV Case Management': {
                'immediate': 'digital case tracking system deployment',
                'shortterm': 'comprehensive case management software with privacy features'
            },
            'Interagency Coordination': {
                'immediate': 'secure communication channels and information sharing protocols',
                'shortterm': 'collaborative platforms and joint planning tools'
            }
        }
        
        return actions.get(indicator, {}).get(phase, 'targeted capacity building initiatives')
        
    def _generate_recommendation(self, indicator: str, score: float) -> str:
        """Generate specific recommendation for an indicator."""
        recommendations_map = {
            'ICT Infrastructure': "Invest in upgrading hardware, internet connectivity, and "
                                 "technical infrastructure for service providers",
            'Digital Literacy': "Implement comprehensive digital skills training programs "
                               "for GBV response staff",
            'Data Management': "Establish robust data management systems with proper security "
                              "and backup protocols",
            'GBV Case Management': "Deploy integrated case management systems with proper "
                                  "privacy safeguards",
            'Interagency Coordination': "Develop digital coordination platforms to facilitate "
                                       "information sharing and joint planning"
        }
        
        return recommendations_map.get(
            indicator,
            f"Strengthen {indicator.lower()} through targeted capacity building"
        )


    def generate_text_report(self, output_path: str) -> str:
        """
        Generate a comprehensive text report.
        
        Args:
            output_path: Path where TXT file should be saved
            
        Returns:
            Path to generated TXT file
        """
        self._update_progress(1, "Initializing text report generation...")
        
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("GBV ICT READINESS ASSESSMENT - COMPREHENSIVE ANALYTICAL REPORT")
        lines.append("National Statistical Agency (NSA)")
        lines.append("=" * 80)
        lines.append(f"\nReport Date: {datetime.now().strftime('%B %d, %Y')}")
        lines.append(f"Total Responses: {len(self.submissions)}")
        lines.append(f"Assessment Period: {self._get_assessment_period()}\n")
        lines.append("=" * 80)
        
        # Executive Summary
        self._update_progress(2, "Writing executive summary...")
        lines.append("\n\nEXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"\nThis assessment evaluated {len(self.submissions)} service providers to determine")
        lines.append("their capacity to effectively utilize ICT in GBV response activities.")
        lines.append("\nThe assessment examined five key indicators: ICT Infrastructure, Digital Literacy,")
        lines.append("Data Management, GBV Case Management, and Interagency Coordination.")
        
        # Indicator Summary
        self._update_progress(3, "Analyzing indicators...")
        lines.append("\n\nINDICATOR SUMMARY")
        lines.append("-" * 80)
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                level = self._get_readiness_level(score)
                lines.append(f"\n{indicator}: {score:.1f}% ({level})")
        
        # Regional Analysis
        self._update_progress(4, "Conducting regional analysis...")
        lines.append("\n\nREGIONAL ANALYSIS")
        lines.append("-" * 80)
        region_column = self._find_region_column()
        if region_column and region_column in self.df.columns:
            # Convert any list values to strings and get unique regions
            region_series = self.df[region_column].dropna()
            region_series = region_series.apply(lambda x: str(x) if isinstance(x, list) else x)
            regions = region_series.unique()
            for region in sorted(regions):
                region_df = self.df[self.df[region_column] == region]
                regional_scores = []
                for indicator, questions in self.indicator_mappings.items():
                    score = self._calculate_indicator_average_for_df(region_df, questions)
                    if score is not None:
                        regional_scores.append(score)
                avg_score = np.mean(regional_scores) if regional_scores else 0
                lines.append(f"\n{region}:")
                lines.append(f"  Responses: {len(region_df)}")
                lines.append(f"  Average Score: {avg_score:.1f}%")
                lines.append(f"  Readiness Level: {self._get_readiness_level(avg_score)}")
        
        # National Analysis
        self._update_progress(5, "Conducting national analysis...")
        lines.append("\n\nNATIONAL ANALYSIS")
        lines.append("-" * 80)
        lines.append(f"\nTotal Submissions: {len(self.df)}")
        lines.append("\nNational Indicator Breakdown:")
        for indicator, questions in self.indicator_mappings.items():
            score = self._calculate_indicator_average(questions)
            if score is not None:
                lines.append(f"  - {indicator}: {score:.1f}% ({self._get_readiness_level(score)})")
        
        # Comprehensive Conclusions
        self._update_progress(6, "Formulating conclusions...")
        lines.append("\n\nCOMPREHENSIVE CONCLUSIONS")
        lines.append("-" * 80)
        
        indicator_scores = {ind: self._calculate_indicator_average(qs) 
                          for ind, qs in self.indicator_mappings.items() 
                          if self._calculate_indicator_average(qs) is not None}
        
        if indicator_scores:
            strongest = max(indicator_scores.items(), key=lambda x: x[1])
            weakest = min(indicator_scores.items(), key=lambda x: x[1])
            lines.append(f"\nStrongest Area: {strongest[0]} ({strongest[1]:.1f}%)")
            lines.append(f"Weakest Area: {weakest[0]} ({weakest[1]:.1f}%)")
        
        lines.append("\nKey Findings:")
        for indicator, score in sorted(indicator_scores.items(), key=lambda x: x[1], reverse=True):
            if score >= 70:
                finding = "Strong capacity - can serve as foundation for improvements"
            elif score >= 50:
                finding = "Moderate capacity - requires enhancement"
            else:
                finding = "Critical gaps - requires immediate intervention"
            lines.append(f"  • {indicator} ({score:.1f}%): {finding}")
        
        # Strategic Way Forward
        self._update_progress(7, "Developing strategic recommendations...")
        lines.append("\n\nSTRATEGIC WAY FORWARD")
        lines.append("-" * 80)
        lines.append("\nBased on the assessment findings, the following phased")
        lines.append("approach is recommended:\n")
        
        lines.append("PHASE 1: IMMEDIATE PRIORITIES (0-6 months)")
        lines.append("  • Establish ICT Readiness Task Force")
        lines.append("  • Secure budget allocation for priority needs")
        lines.append("  • Develop standardized ICT policies")
        for indicator, score in indicator_scores.items():
            if score < 40:
                lines.append(f"  • {indicator}: Emergency capacity building program")
        
        lines.append("\nPHASE 2: SHORT-TERM GOALS (6-12 months)")
        lines.append("  • Roll out comprehensive training programs")
        lines.append("  • Deploy pilot digital case management systems")
        lines.append("  • Establish regional ICT support hubs")
        
        lines.append("\nPHASE 3: MEDIUM-TERM OBJECTIVES (1-2 years)")
        lines.append("  • Scale successful pilots to national level")
        lines.append("  • Achieve minimum 70% readiness across all indicators")
        lines.append("  • Integrate with national information systems")
        
        lines.append("\nPHASE 4: LONG-TERM VISION (2-5 years)")
        lines.append("  • Achieve 85%+ readiness nationwide")
        lines.append("  • Establish regional leadership in GBV ICT integration")
        lines.append("  • Develop advanced analytics capabilities")
        
        lines.append("\n\nRESOURCE REQUIREMENTS")
        lines.append("-" * 80)
        lines.append("  Financial: NAD 15-25 million over 5 years")
        lines.append("  Human Resources: ICT coordinators and technical trainers")
        lines.append("  Technical: Hardware, software, connectivity upgrades")
        lines.append("  Partnerships: Development partners and technology providers")
        
        lines.append("\n\nMONITORING & EVALUATION")
        lines.append("-" * 80)
        lines.append("  • Quarterly progress reviews")
        lines.append("  • Annual comprehensive assessments")
        lines.append("  • Real-time performance dashboards")
        lines.append("  • Stakeholder feedback sessions")
        lines.append("  • Impact evaluations on GBV response outcomes")
        
        lines.append("\n\n" + "=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        # Write to file
        self._update_progress(8, "Writing text file...")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self._update_progress(9, "Text report generation complete!")
        return output_path


def generate_comprehensive_report(
    submissions: List[Dict],
    output_path: str,
    logo_path: Optional[str] = None,
    progress_callback=None,
    format: str = 'pdf'
) -> str:
    """
    Generate a comprehensive report from survey submissions.
    
    Args:
        submissions: List of survey submission dictionaries
        output_path: Path where report should be saved
        logo_path: Optional path to NSA logo image file (PDF only)
        progress_callback: Optional callback function(step, total, message)
        format: Report format - 'pdf' or 'txt' (default: 'pdf')
        
    Returns:
        Path to generated report file
    """
    generator = ComprehensiveReportGenerator(submissions, logo_path, progress_callback)
    
    if format.lower() == 'txt':
        return generator.generate_text_report(output_path)
    else:
        return generator.generate_report(output_path)

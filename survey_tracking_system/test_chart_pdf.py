"""Test PDF generation with Plotly charts."""
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import plotly.express as px
import pandas as pd

def test_pdf_with_charts():
    """Test PDF generation with embedded Plotly charts."""
    print("Testing PDF generation with Plotly charts...")
    
    try:
        # Create sample data
        data = pd.DataFrame({
            'Institution': ['Institution A', 'Institution B', 'Institution C', 'Institution D'],
            'Submissions': [45, 38, 52, 30]
        })
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        story.append(Paragraph('Test PDF with Charts', styles['Title']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph('This tests Plotly chart rendering in PDF.', styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Create chart
        print("Creating Plotly chart...")
        fig = px.bar(data, x='Institution', y='Submissions', title='Test Chart')
        fig.update_layout(width=700, height=500)
        
        # Render to PNG
        print("Rendering chart to PNG...")
        png_bytes = fig.to_image(format='png', engine='kaleido')
        
        # Add to PDF
        print("Adding chart to PDF...")
        img = RLImage(BytesIO(png_bytes), width=6*inch, height=4*inch)
        story.append(img)
        
        story.append(PageBreak())
        story.append(Paragraph('End of test report', styles['Normal']))
        
        # Build PDF
        print("Building PDF...")
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        
        # Save to file
        output_path = 'test_chart_output.pdf'
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ SUCCESS! PDF with chart generated: {output_path}")
        print(f"PDF size: {len(pdf_bytes)} bytes")
        
        # Verify PDF header
        if pdf_bytes[:4] == b'%PDF':
            print("✅ Valid PDF header detected")
            return True
        else:
            print(f"⚠️ Warning: Invalid PDF header")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = test_pdf_with_charts()
    sys.exit(0 if success else 1)

"""Simple test to verify reportlab PDF generation works."""
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def test_basic_pdf():
    """Test basic PDF generation with reportlab."""
    print("Testing basic PDF generation with reportlab...")
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        story.append(Paragraph('Test PDF Report', styles['Title']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph('This is a test to verify PDF generation works correctly.', styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        
        # Save to file
        output_path = 'test_basic_output.pdf'
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ SUCCESS! Basic PDF generated: {output_path}")
        print(f"PDF size: {len(pdf_bytes)} bytes")
        
        # Verify PDF header
        if pdf_bytes[:4] == b'%PDF':
            print("✅ Valid PDF header detected")
            return True
        else:
            print(f"⚠️ Warning: Invalid PDF header. First bytes: {pdf_bytes[:20]}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = test_basic_pdf()
    sys.exit(0 if success else 1)

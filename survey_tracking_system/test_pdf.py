"""Test PDF generation to ensure it works correctly."""
import sys
import os

# Add frontend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'frontend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Now import after path is set
import requests
from frontend.reporting import generate_consolidated_pdf

def test_pdf_generation():
    """Test PDF generation with real data from backend."""
    print("Testing PDF generation...")
    
    try:
        # Fetch data from backend
        response = requests.get('http://localhost:5001/api/kobo/submissions')
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            return False
        
        data = response.json()
        submissions = data.get('submissions', [])
        
        if not submissions:
            print("No submissions found. Creating test data...")
            submissions = [
                {
                    'grp_login/institution_name': 'Test Institution 1',
                    'grp_login/resp_region_display': 'Kavango',
                    '_submission_time': '2026-01-20T10:00:00',
                    'test_question': 'yes'
                },
                {
                    'grp_login/institution_name': 'Test Institution 2',
                    'grp_login/resp_region_display': 'Hardap',
                    '_submission_time': '2026-01-20T11:00:00',
                    'test_question': 'no'
                }
            ]
        
        print(f"Found {len(submissions)} submissions")
        
        # Generate PDF
        print("Generating PDF...")
        pdf_bytes = generate_consolidated_pdf(submissions)
        
        if not pdf_bytes:
            print("ERROR: PDF generation returned empty bytes")
            return False
        
        # Save to file
        output_path = os.path.join(os.path.dirname(__file__), 'test_output.pdf')
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ SUCCESS! PDF generated: {output_path}")
        print(f"PDF size: {len(pdf_bytes)} bytes")
        
        # Verify it starts with PDF header
        if pdf_bytes[:4] == b'%PDF':
            print("✅ Valid PDF header detected")
        else:
            print(f"⚠️ Warning: PDF header not found. First bytes: {pdf_bytes[:20]}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_pdf_generation()
    sys.exit(0 if success else 1)

"""
CloudGuard - 2-Page Validation Guide
"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

class Guide(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'Confidential - ICICI Prudential AMC | CloudGuard', new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

def run():
    pdf = Guide()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ========== PAGE 1 ==========
    pdf.add_page()
    
    # Title
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(0, 10, 'CloudGuard', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, 'Application Validation Guide', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_draw_color(20, 55, 110)
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
    pdf.ln(6)
    
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, 'Steps to access the application and perform a validation flow.')
    pdf.ln(3)
    
    # --- STEP 1 ---
    pdf.set_fill_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 7, '  STEP 1 :  Login to the Application', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(3)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, '1.  Open a web browser (Chrome / Edge recommended).\n2.  Navigate to the application URL :')
    pdf.ln(1)
    pdf.set_fill_color(235, 245, 255)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(190, 8, '     http://10.238.46.116', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(2)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, '3.  Enter the login credentials and click "Sign In":')
    pdf.ln(1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(30, 6, '     Email:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, '  admin@krelixir.com', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(30, 6, '     Password:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, '  CloudGuard@2026!', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.multi_cell(0, 5, '4.  Upon successful login you will be redirected to the Dashboard.')
    pdf.ln(3)
    
    # --- STEP 2 ---
    pdf.set_fill_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 7, '  STEP 2 :  Run the AI Pipeline', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(3)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, '1.  On the Dashboard, locate the Pipeline Control panel on the right side of the screen.\n2.  Click the "Run Pipeline" button (play icon).\n3.  A date-picker dialog will appear. Select the Start Date and End Date for the\n     analysis period (the duration of the run).')
    pdf.ln(1)
    
    # Note
    pdf.set_fill_color(255, 248, 230)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(160, 100, 0)
    pdf.cell(190, 6, '  NOTE', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(80, 60, 0)
    pdf.multi_cell(0, 5, '  - Dates before 31 March 2026: Logs are fetched from Azure Blob Storage (historical data).\n  - Dates after 31 March 2026: Logs are fetched from Azure Log Analytics (real-time data).')
    pdf.ln(2)
    
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, '4.  Click "Start Pipeline" to begin. The pipeline will run through 8 AI agents:\n     Log Collection -> Preprocessing -> AI Classification -> Root Cause Analysis\n     -> Priority Assignment -> Context Enrichment -> Resolution -> Email Notification\n5.  The pipeline typically completes in 1-3 minutes. Status is shown on the Dashboard.')
    pdf.ln(3)
    
    # --- STEP 3 ---
    pdf.set_fill_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 7, '  STEP 3 :  Receive Email Notification', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(3)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, 'After the pipeline run completes, an email will be triggered automatically if any incidents\nare discovered during the analysis phase.\n\n- P1 (Critical) and P2 (High) incidents trigger email alerts immediately.\n- P3 (Medium) incidents are visible only on the Dashboard (no email).\n- If no incidents are found, a summary "No Issues Detected" email is sent.')
    pdf.ln(1)
    
    # Note
    pdf.set_fill_color(230, 245, 255)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(190, 6, '  NOTE', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(0, 5, '  There might be a slight delay in logs getting populated in the cloud - this is by design.\n  Azure diagnostic logs can take a few minutes to appear in Log Analytics or Blob Storage.')
    
    # ========== PAGE 2 ==========
    pdf.add_page()
    
    # Title
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(0, 8, 'CloudGuard - Validation Guide (contd.)', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_draw_color(20, 55, 110)
    pdf.line(10, pdf.get_y()+1, 200, pdf.get_y()+1)
    pdf.ln(5)
    
    # --- STEP 4 ---
    pdf.set_fill_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 7, '  STEP 4 :  Validate the Incident Email', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(3)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, 'In the email received, validate the following details of the reported incident:')
    pdf.ln(2)
    
    # Table
    pdf.set_fill_color(240, 245, 255)
    pdf.set_draw_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(55, 7, '  Field', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
    pdf.cell(135, 7, '  What to Check', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    
    rows = [
        ('Incident Title', 'The short description of the issue detected by the AI.'),
        ('Priority', 'P1 (Critical), P2 (High), or P3 (Medium).'),
        ('Services Affected', 'Which Azure services are impacted (e.g., Front Door, App Service).'),
        ('Number of Logs', 'Total error log count found during the analysis period.'),
        ('Root Cause', 'AI-generated explanation of why the error occurred.'),
        ('Resolution Steps', 'Recommended actions to fix the issue.'),
        ('Business Impact', 'Assessment of how the issue affects end-users.'),
        ('Owner Team', 'Which team should own the resolution.'),
    ]
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(40, 40, 40)
    for field, desc in rows:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(55, 7, f'  {field}', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(135, 7, f'  {desc}', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    pdf.ln(5)
    
    # --- STEP 5 ---
    pdf.set_fill_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 7, '  STEP 5 :  Review on the Dashboard', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(3)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, '1.  Return to the Dashboard to see the incident reflected in the Recent Incidents table.\n2.  Click on any incident row to view full details, Root Cause Analysis, and Resolution.\n3.  Review the Service Health Topology to see which services are affected (shown in red).\n4.  Check the Pipeline Runs page (top nav) to confirm the run completed successfully.')
    pdf.ln(4)
    
    # Quick Reference
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(20, 55, 110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(20, 55, 110)
    pdf.cell(190, 7, '  Quick Reference', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.ln(2)
    
    refs = [
        ('Application URL', 'http://10.238.46.116'),
        ('Data before 31 Mar 2026', 'Azure Blob Storage (historical)'),
        ('Data after 31 Mar 2026', 'Azure Log Analytics (real-time)'),
        ('Email Recipients', 'prabhat_singh@ext.icicipruamc.com'),
        ('Pipeline Duration', '1 - 3 minutes (varies by date range)'),
        ('Support Team', 'KR Elixir'),
    ]
    pdf.set_text_color(40, 40, 40)
    for key, val in refs:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(50, 6, f'  {key}', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(0, 6, f':   {val}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(4)
    
    # Important
    pdf.set_fill_color(255, 240, 240)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(180, 30, 30)
    pdf.cell(190, 6, '  IMPORTANT', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(120, 30, 30)
    pdf.multi_cell(0, 5, '  This application is accessible only from the corporate network. Ensure VPN connectivity\n  if accessing from outside the office. The platform supports up to 5-6 concurrent users.')
    
    # Save
    out = r'c:\Users\krelixiradmin\Downloads\Cloud_Guard\CloudGuard_Validation_Guide.pdf'
    pdf.output(out)
    print(f"PDF generated: {out}")
    print(f"Size: {os.path.getsize(out):,} bytes")
    print(f"Pages: {pdf.pages_count}")

if __name__ == '__main__':
    run()

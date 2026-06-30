"""
CloudGuard KR Elixir — User Guide PDF Generator
Generates a comprehensive step-by-step guide for using the CloudGuard dashboard.
"""

from fpdf import FPDF
import os

class CloudGuardGuide(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
    
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, 'CloudGuard KR Elixir - User Guide', 0, 0, 'L')
            self.cell(0, 8, f'Page {self.page_no()}', 0, 1, 'R')
            self.line(10, 16, 200, 16)
            self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'Confidential - ICICI Prudential AMC | KR Elixir Team', 0, 0, 'C')
    
    def chapter_title(self, num, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(20, 60, 120)
        self.cell(0, 12, f'{num}. {title}', 0, 1, 'L')
        self.set_draw_color(20, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)
    
    def section_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(40, 80, 140)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
    
    def step(self, num, text):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 100, 60)
        self.cell(25, 7, f'Step {num}:', 0, 0, 'L')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 7, text)
        self.ln(2)
    
    def bullet(self, text, indent=15):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(60, 60, 60)
        self.cell(5, 6, '-', 0, 0)
        self.multi_cell(0, 6, f'  {text}')
        self.ln(1)
    
    def note_box(self, text, box_type='NOTE'):
        colors = {
            'NOTE': (220, 235, 255, 30, 80, 160),
            'TIP': (220, 245, 220, 30, 120, 30),
            'WARNING': (255, 245, 220, 180, 120, 20),
            'IMPORTANT': (255, 230, 230, 180, 30, 30),
        }
        bg_r, bg_g, bg_b, txt_r, txt_g, txt_b = colors.get(box_type, colors['NOTE'])
        
        self.set_fill_color(bg_r, bg_g, bg_b)
        self.set_draw_color(txt_r, txt_g, txt_b)
        
        y_start = self.get_y()
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(txt_r, txt_g, txt_b)
        self.cell(0, 7, f'  {box_type}', 0, 1, 'L', fill=True)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, f'  {text}', fill=True)
        self.ln(4)
    
    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(3)
    
    def key_value(self, key, value):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(60, 60, 60)
        self.cell(45, 7, f'{key}:', 0, 0)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(40, 40, 40)
        self.cell(0, 7, value, 0, 1)


def generate_guide():
    pdf = CloudGuardGuide()
    
    # ── Cover Page ──
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 15, 'CloudGuard KR Elixir', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 18)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, 'User Guide', 0, 1, 'C')
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, 'AI-Powered Azure Incident Detection & Response Platform', 0, 1, 'C')
    pdf.ln(20)
    
    pdf.set_draw_color(20, 60, 120)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(15)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, 'Version: 2.0.0', 0, 1, 'C')
    pdf.cell(0, 8, 'Date: June 2026', 0, 1, 'C')
    pdf.cell(0, 8, 'Team: KR Elixir', 0, 1, 'C')
    pdf.cell(0, 8, 'Organization: ICICI Prudential AMC', 0, 1, 'C')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 8, 'Application URL: http://10.238.46.116', 0, 1, 'C')
    
    # ── Table of Contents ──
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 15, 'Table of Contents', 0, 1, 'L')
    pdf.ln(5)
    
    toc = [
        ('1', 'Getting Started - Login', '3'),
        ('2', 'Dashboard Overview', '4'),
        ('3', 'Running the AI Pipeline', '6'),
        ('4', 'Viewing Incidents', '8'),
        ('5', 'Incident Details & Root Cause Analysis', '9'),
        ('6', 'Service Health Topology', '10'),
        ('7', 'Log Explorer', '11'),
        ('8', 'Pipeline Runs History', '12'),
        ('9', 'Golden Signals & Analytics', '13'),
        ('10', 'Email Notifications', '14'),
        ('11', 'Troubleshooting & FAQ', '15'),
    ]
    for num, title, page in toc:
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(10, 8, num, 0, 0)
        pdf.cell(140, 8, title, 0, 0)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, page, 0, 1, 'R')
    
    # ── Chapter 1: Getting Started ──
    pdf.add_page()
    pdf.chapter_title('1', 'Getting Started - Login')
    
    pdf.body_text('CloudGuard KR Elixir is a web-based application accessible from any modern browser on the corporate network. Follow these steps to log in:')
    
    pdf.step(1, 'Open your web browser (Chrome, Edge, or Firefox recommended)')
    pdf.step(2, 'Navigate to: http://10.238.46.116')
    pdf.step(3, 'You will see the CloudGuard login page with the application logo and a sign-in form')
    pdf.step(4, 'Enter your credentials:')
    pdf.key_value('Email', 'admin@krelixir.com')
    pdf.key_value('Password', 'CloudGuard@2026!')
    pdf.ln(2)
    pdf.step(5, 'Click the "Sign In" button')
    pdf.step(6, 'You will be redirected to the main Dashboard')
    
    pdf.note_box('The application supports 5-6 concurrent users. Multiple team members can access the dashboard simultaneously without performance issues.', 'NOTE')
    
    pdf.note_box('If the login page does not load, ensure you are connected to the corporate network or VPN. The application is only accessible from the internal network.', 'TIP')
    
    # ── Chapter 2: Dashboard Overview ──
    pdf.add_page()
    pdf.chapter_title('2', 'Dashboard Overview')
    
    pdf.body_text('After logging in, you will see the main Dashboard. This is the central hub of CloudGuard KR Elixir, providing a real-time overview of your Azure infrastructure health.')
    
    pdf.section_title('2.1 Dashboard Layout')
    pdf.body_text('The dashboard is divided into several key sections:')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 8, 'A. Top Navigation Bar', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.bullet('Application title: "CloudGuard KR Elixir"')
    pdf.bullet('Navigation links: Dashboard, Log Explorer, Pipeline Runs')
    pdf.bullet('User profile icon and logout button (top-right corner)')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 8, 'B. Summary Cards (Top Row)', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.bullet('Total Incidents: Shows count of all detected incidents')
    pdf.bullet('P1 Critical: Number of Priority 1 (critical) incidents')
    pdf.bullet('P2 High: Number of Priority 2 (high) incidents')
    pdf.bullet('P3 Medium: Number of Priority 3 (medium) incidents')
    pdf.bullet('Logs Analyzed: Total number of Azure logs processed')
    pdf.bullet('Pipeline Health: Current pipeline status indicator')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 8, 'C. Main Content Panels', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.bullet('Recent Incidents Table: List of latest incidents with priority, title, service, and time')
    pdf.bullet('Service Health Topology: Visual map showing Azure service status (green/red)')
    pdf.bullet('Pipeline Health Ring: Donut chart showing pipeline run success rate')
    pdf.bullet('Log Volume Chart: Time-series chart showing log ingestion volume over 24 hours')
    pdf.bullet('Golden Signals: Key metrics (Error Rate, Latency, Traffic, Saturation)')

    pdf.add_page()
    pdf.section_title('2.2 Understanding Status Colors')
    pdf.body_text('Throughout the dashboard, colors indicate the health status of services and incidents:')
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(220, 245, 220)
    pdf.cell(30, 7, '  GREEN', 0, 0, 'L', fill=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 7, '  Healthy / No Issues / Resolved', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(255, 245, 220)
    pdf.cell(30, 7, '  YELLOW', 0, 0, 'L', fill=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 7, '  Warning / P3 Medium severity', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(255, 220, 220)
    pdf.cell(30, 7, '  RED', 0, 0, 'L', fill=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 7, '  Critical / P1-P2 severity / Service Down', 0, 1)
    pdf.ln(2)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(30, 7, '  GREY', 0, 0, 'L', fill=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 7, '  Unknown / Not Configured / No Data', 0, 1)
    pdf.ln(5)

    # ── Chapter 3: Running the AI Pipeline ──
    pdf.add_page()
    pdf.chapter_title('3', 'Running the AI Pipeline')
    
    pdf.body_text('The AI Pipeline is the core of CloudGuard KR Elixir. It collects Azure logs, analyzes them using Google Gemini AI, classifies incidents, generates root cause analysis, and sends email alerts.')
    
    pdf.section_title('3.1 Automatic Pipeline Runs')
    pdf.body_text('The pipeline runs automatically every 48 hours. You can see the next scheduled run time on the Dashboard under "Pipeline Status".')
    
    pdf.section_title('3.2 Manual Pipeline Run (On-Demand)')
    pdf.body_text('To run the pipeline manually for a specific date range:')
    
    pdf.step(1, 'On the Dashboard, locate the "Run Pipeline" button (blue play icon) in the Pipeline Control section at the top-right area')
    pdf.step(2, 'Click the "Run Pipeline" button. A date picker dialog will appear')
    pdf.step(3, 'Select the Start Date and End Date for the log analysis period')
    
    pdf.note_box('Data Source Routing:\n- Dates BEFORE March 31, 2026: Logs are pulled from Azure Blob Storage (historical data)\n- Dates AFTER March 31, 2026: Logs are pulled from Azure Log Analytics (real-time data)', 'IMPORTANT')
    
    pdf.step(4, 'Click "Start Pipeline" to begin the analysis')
    pdf.step(5, 'The pipeline will process through 8 AI agents (shown as animated nodes on the dashboard):')
    pdf.bullet('Agent 1 - Log Collector: Fetches logs from Azure')
    pdf.bullet('Agent 2 - Preprocessor: Cleans and normalizes log data')
    pdf.bullet('Agent 3 - Classifier: AI classifies logs into incident types')
    pdf.bullet('Agent 3.5 - RCA: Root Cause Analysis using Gemini AI')
    pdf.bullet('Agent 4 - Priority: Assigns P1/P2/P3 severity')
    pdf.bullet('Agent 5 - Context: Enriches with historical data')
    pdf.bullet('Agent 6 - Resolution: Generates fix recommendations')
    pdf.bullet('Agent 7 - Orchestrator: Coordinates email notifications')
    pdf.bullet('Agent 8 - Notification: Sends email alerts for P1/P2 incidents')
    
    pdf.step(6, 'Wait for the pipeline to complete (typically 1-3 minutes). The status will show "Completed" with a green checkmark')
    pdf.step(7, 'Refresh the Dashboard to see newly detected incidents')
    
    pdf.note_box('While the pipeline is running, you can continue using the dashboard. The pipeline runs asynchronously in the background.', 'TIP')

    # ── Chapter 4: Viewing Incidents ──
    pdf.add_page()
    pdf.chapter_title('4', 'Viewing Incidents')
    
    pdf.body_text('After a pipeline run, detected incidents appear in the Recent Incidents table on the Dashboard.')
    
    pdf.section_title('4.1 Incident Table Columns')
    pdf.bullet('Priority: P1 (Critical - Red), P2 (High - Orange), P3 (Medium - Yellow)')
    pdf.bullet('Title: Short description of the incident')
    pdf.bullet('Service: The affected Azure service (e.g., Azure Front Door, App Service)')
    pdf.bullet('Category: Incident type (e.g., WAF Block, Backend Error, SSL Warning)')
    pdf.bullet('Status: OPEN, IN_PROGRESS, RESOLVED, or CLOSED')
    pdf.bullet('Time: When the incident was detected')
    
    pdf.section_title('4.2 Filtering Incidents')
    pdf.step(1, 'Use the Priority filter buttons (All, P1, P2, P3) to filter by severity')
    pdf.step(2, 'Use the search bar to search by incident title or service name')
    pdf.step(3, 'Use the date range picker to filter incidents by time period')
    
    pdf.section_title('4.3 Incident Actions')
    pdf.bullet('Click on any incident row to view full details including root cause analysis')
    pdf.bullet('Use the "Acknowledge" button to mark an incident as being investigated')
    pdf.bullet('Use the "Resolve" button to mark an incident as resolved')
    
    # ── Chapter 5: Incident Details & RCA ──
    pdf.add_page()
    pdf.chapter_title('5', 'Incident Details & Root Cause Analysis')
    
    pdf.body_text('Clicking on an incident opens a detailed view with comprehensive information generated by the AI pipeline.')
    
    pdf.section_title('5.1 Incident Detail View')
    pdf.body_text('The incident detail page shows:')
    pdf.bullet('Incident Title and Priority badge')
    pdf.bullet('Affected Azure Service and Resource name')
    pdf.bullet('Description: AI-generated summary of what happened')
    pdf.bullet('Root Cause Analysis: Specific explanation of why the error occurred')
    pdf.bullet('Recommended Resolution: Step-by-step fix instructions')
    pdf.bullet('Business Impact: Assessment of how this affects users')
    pdf.bullet('Owner Team: Which team should handle the resolution')
    pdf.bullet('Estimated Resolution Time: Expected time to fix')
    
    pdf.section_title('5.2 Root Cause Analysis (RCA)')
    pdf.body_text('The RCA section provides AI-generated analysis based on actual error logs. It includes:')
    pdf.bullet('Root Cause Category: e.g., "WAF Geo-Blocking", "SQL Lock Timeout", "SSL Certificate Warning"')
    pdf.bullet('Confidence Score: How confident the AI is in its analysis (0.0 - 1.0)')
    pdf.bullet('Evidence: Actual log samples that support the root cause determination')
    pdf.bullet('Affected Component: Specific Azure resource affected')
    pdf.bullet('Immediate Resolution: What to do right now to fix the issue')
    pdf.bullet('Preventive Action: What to do to prevent recurrence')
    
    pdf.note_box('The RCA is generated by Google Gemini AI analyzing the actual error log content. It references specific error codes, URLs, IP addresses, and Azure resource names found in the logs.', 'NOTE')

    # ── Chapter 6: Service Health Topology ──
    pdf.add_page()
    pdf.chapter_title('6', 'Service Health Topology')
    
    pdf.body_text('The Service Health Topology panel shows a visual map of your Azure infrastructure services and their real-time health status.')
    
    pdf.section_title('6.1 Services Monitored')
    pdf.bullet('Azure Front Door (CDN & Global Load Balancer)')
    pdf.bullet('Azure WAF (Web Application Firewall)')
    pdf.bullet('Azure App Gateway (L7 Application Gateway)')
    pdf.bullet('Azure App Service (Web Application Hosting)')
    pdf.bullet('Azure Blob Storage (Object & File Storage)')
    pdf.bullet('Azure Log Analytics (Log Collection & Query)')
    pdf.bullet('CloudGuard Backend (API Server)')
    
    pdf.section_title('6.2 Health Status Indicators')
    pdf.body_text('Each service node shows:')
    pdf.bullet('Green circle: Service is healthy and responding')
    pdf.bullet('Red circle: Service is down or has active incidents')
    pdf.bullet('Grey circle: Service not configured or no endpoint set')
    pdf.bullet('Response time in milliseconds')
    pdf.bullet('HTTP status code from health check')
    
    pdf.section_title('6.3 How Health Checks Work')
    pdf.body_text('CloudGuard sends HTTP HEAD/GET requests to each service endpoint every 8 seconds. The health check verifies:')
    pdf.bullet('The service responds within the timeout period (8 seconds)')
    pdf.bullet('The HTTP status code is 2xx or 3xx (healthy)')
    pdf.bullet('No active incidents exist for that service in the last 24 hours')

    # ── Chapter 7: Log Explorer ──
    pdf.add_page()
    pdf.chapter_title('7', 'Log Explorer')
    
    pdf.body_text('The Log Explorer allows you to browse and search through all processed Azure logs.')
    
    pdf.section_title('7.1 Accessing the Log Explorer')
    pdf.step(1, 'Click "Log Explorer" in the top navigation bar')
    pdf.step(2, 'The page shows a searchable, filterable table of all cloud logs')
    
    pdf.section_title('7.2 Log Explorer Features')
    pdf.bullet('Search: Full-text search across log messages, sources, and categories')
    pdf.bullet('Filter by Level: ERROR, WARNING, INFO')
    pdf.bullet('Filter by Source: Azure Front Door, App Service, App Gateway, etc.')
    pdf.bullet('Date Range: Filter logs by time period')
    pdf.bullet('Pagination: Navigate through large result sets')
    
    pdf.section_title('7.3 Exporting Logs')
    pdf.step(1, 'Apply your desired filters')
    pdf.step(2, 'Click the "Export CSV" button at the top-right of the log table')
    pdf.step(3, 'A CSV file will be downloaded containing the filtered log data')
    
    pdf.note_box('Exported CSV files include: Timestamp, Level, Source, Category, Message, Resource ID, and Operation Name.', 'TIP')

    # ── Chapter 8: Pipeline Runs History ──
    pdf.add_page()
    pdf.chapter_title('8', 'Pipeline Runs History')
    
    pdf.body_text('The Pipeline Runs page shows the history of all pipeline executions.')
    
    pdf.section_title('8.1 Accessing Pipeline History')
    pdf.step(1, 'Click "Pipeline Runs" in the top navigation bar')
    pdf.step(2, 'You will see a table of all past pipeline runs with their results')
    
    pdf.section_title('8.2 Pipeline Run Details')
    pdf.body_text('Each pipeline run entry shows:')
    pdf.bullet('Run ID: Unique identifier for the run')
    pdf.bullet('Trigger Type: "manual" or "scheduled"')
    pdf.bullet('Status: COMPLETED, RUNNING, or FAILED')
    pdf.bullet('Started At / Completed At: Timestamps')
    pdf.bullet('Duration: How long the pipeline took (in seconds)')
    pdf.bullet('Logs Processed: Number of Azure logs analyzed')
    pdf.bullet('Incidents Created: Number of incidents detected')
    pdf.bullet('P1/P2/P3 Count: Breakdown by priority')
    pdf.bullet('Emails Sent: Number of notification emails delivered')
    
    pdf.section_title('8.3 Pipeline Health Ring')
    pdf.body_text('The Pipeline Health Ring on the Dashboard shows the success rate of recent pipeline runs as a donut chart. A green ring indicates all runs completed successfully.')

    # ── Chapter 9: Golden Signals ──
    pdf.add_page()
    pdf.chapter_title('9', 'Golden Signals & Analytics')
    
    pdf.body_text('The Golden Signals panel displays the four key metrics that indicate the health of your Azure services (based on Google SRE principles).')
    
    pdf.section_title('9.1 The Four Golden Signals')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(200, 50, 50)
    pdf.cell(0, 8, '1. Error Rate', 0, 1)
    pdf.body_text('Percentage of log entries that are errors (4xx/5xx HTTP responses, exceptions). A high error rate indicates service degradation.')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(200, 120, 0)
    pdf.cell(0, 8, '2. Latency', 0, 1)
    pdf.body_text('Average response time of your services. High latency means users experience slow page loads.')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 120, 180)
    pdf.cell(0, 8, '3. Traffic', 0, 1)
    pdf.body_text('Volume of requests being processed. Unusual spikes or drops may indicate issues.')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(120, 0, 180)
    pdf.cell(0, 8, '4. Saturation', 0, 1)
    pdf.body_text('How close your services are to capacity. High saturation means risk of overload.')

    # ── Chapter 10: Email Notifications ──
    pdf.add_page()
    pdf.chapter_title('10', 'Email Notifications')
    
    pdf.body_text('CloudGuard automatically sends email notifications when incidents are detected.')
    
    pdf.section_title('10.1 When Emails Are Sent')
    pdf.bullet('P1 (Critical) incidents: Email sent immediately to all configured recipients')
    pdf.bullet('P2 (High) incidents: Email sent immediately to all configured recipients')
    pdf.bullet('P3 (Medium) incidents: No email sent (dashboard only)')
    pdf.bullet('All Systems Healthy: A "No Issues Found" summary email is sent if no incidents are detected')
    
    pdf.section_title('10.2 Email Content')
    pdf.body_text('Each incident email includes:')
    pdf.bullet('Priority badge (P1/P2) with color coding')
    pdf.bullet('Incident title and affected service')
    pdf.bullet('Date/time range of the incident')
    pdf.bullet('Root cause analysis summary')
    pdf.bullet('Recommended resolution steps')
    pdf.bullet('Business impact assessment')
    pdf.bullet('Owner team assignment')
    
    pdf.section_title('10.3 Email Recipients')
    pdf.body_text('Emails are sent via Microsoft Graph API to configured recipients. Current recipients:')
    pdf.bullet('Saili_Jaguste@ext.icicipruamc.com')
    pdf.bullet('prabhat_singh@ext.icicipruamc.com')
    
    pdf.note_box('To add or change email recipients, update the notification configuration in the backend settings.', 'NOTE')

    # ── Chapter 11: Troubleshooting ──
    pdf.add_page()
    pdf.chapter_title('11', 'Troubleshooting & FAQ')
    
    pdf.section_title('Q1: The dashboard shows no data')
    pdf.body_text('Run the pipeline manually by clicking the "Run Pipeline" button. Select a date range and start the analysis. Data will appear after the pipeline completes (1-3 minutes).')
    
    pdf.section_title('Q2: Pipeline shows "No incidents detected"')
    pdf.body_text('This means the AI analyzed the logs and found no critical, high, or medium severity issues. Try a different date range, or check if the Azure services had any actual errors during that period.')
    
    pdf.section_title('Q3: Some services show as "Down" in topology')
    pdf.body_text('The health check pings each service endpoint. A "Down" status could mean:\n- The service is actually down\n- The VM cannot reach that service (network/firewall restriction)\n- The service endpoint URL is not configured in the .env file')
    
    pdf.section_title('Q4: Emails are not being received')
    pdf.body_text('Check:\n- The Microsoft Graph API credentials are valid\n- The sender email (graph_sender_email) is correctly configured\n- The recipient email addresses are correct\n- P3 incidents do not trigger emails (by design)')
    
    pdf.section_title('Q5: How to restart the application')
    pdf.body_text('Run the startup script:\n  C:\\Users\\krelixiradmin\\Downloads\\Cloud_Guard\\start_production.bat\n\nOr use the command:\n  cd C:\\Users\\krelixiradmin\\Downloads\\Cloud_Guard\\backend\n  venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 80')
    
    pdf.section_title('Q6: What date range should I use?')
    pdf.body_text('- For historical analysis (before March 31, 2026): Data comes from Azure Blob Storage\n- For recent/current analysis (after March 31, 2026): Data comes from Azure Log Analytics\n- For best results, use date ranges of 1-7 days')

    # ── Quick Reference Card ──
    pdf.add_page()
    pdf.chapter_title('', 'Quick Reference Card')
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 10, 'Application Access', 0, 1)
    pdf.key_value('URL', 'http://10.238.46.116')
    pdf.key_value('Email', 'admin@krelixir.com')
    pdf.key_value('Password', 'CloudGuard@2026!')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 10, 'Key Shortcuts', 0, 1)
    pdf.key_value('Dashboard', 'Click "Dashboard" in top nav')
    pdf.key_value('Run Pipeline', 'Click play button on Dashboard')
    pdf.key_value('View Logs', 'Click "Log Explorer" in top nav')
    pdf.key_value('Export CSV', 'Click "Export" in Log Explorer')
    pdf.key_value('Pipeline History', 'Click "Pipeline Runs" in top nav')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 10, 'Priority Levels', 0, 1)
    pdf.key_value('P1 Critical', 'Immediate attention required. Email sent automatically')
    pdf.key_value('P2 High', 'Urgent investigation needed. Email sent automatically')
    pdf.key_value('P3 Medium', 'Monitor and review. Dashboard only, no email')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 10, 'Support', 0, 1)
    pdf.key_value('Team', 'KR Elixir')
    pdf.key_value('VM', 'IPRU-INC-PROD-K (10.238.46.116)')
    pdf.key_value('Startup Script', 'Cloud_Guard\\start_production.bat')
    
    # Save
    output_path = r'c:\Users\krelixiradmin\Downloads\Cloud_Guard\CloudGuard_KR_Elixir_User_Guide.pdf'
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    print(f"File size: {os.path.getsize(output_path):,} bytes")

if __name__ == "__main__":
    generate_guide()

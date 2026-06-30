"""
Convert CloudGuard Validation Checklist to PDF.
Uses reportlab to create a professional PDF from the checklist data.
"""

import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
except ImportError:
    print("Installing reportlab...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ── Colour palette ──
DARK_BLUE = colors.HexColor("#1B2A4A")
MEDIUM_BLUE = colors.HexColor("#2D4A7A")
LIGHT_BLUE = colors.HexColor("#D6E4F0")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
WHITE = colors.white

# ── Styles ──
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title2", parent=styles["Title"],
    fontSize=20, textColor=DARK_BLUE, spaceAfter=6, alignment=TA_CENTER,
)
subtitle_style = ParagraphStyle(
    "Subtitle2", parent=styles["Normal"],
    fontSize=10, textColor=colors.HexColor("#666666"), alignment=TA_CENTER, spaceAfter=16,
)
section_style = ParagraphStyle(
    "Section", parent=styles["Normal"],
    fontSize=10, textColor=WHITE, fontName="Helvetica-Bold",
)
header_style = ParagraphStyle(
    "Header", parent=styles["Normal"],
    fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER,
)
body_style = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=7.5, textColor=colors.HexColor("#333333"), leading=10,
)
body_center = ParagraphStyle(
    "BodyCenter", parent=body_style, alignment=TA_CENTER,
)
signoff_header = ParagraphStyle(
    "SignoffHeader", parent=styles["Normal"],
    fontSize=14, textColor=DARK_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER,
    spaceBefore=20, spaceAfter=10,
)


# ── Feature Data ──
SECTIONS = [
    (
        "A. Network & Infrastructure Monitoring (VP - Networking)",
        [
            ("Azure Front Door Log Ingestion",
             "Verify that CloudGuard pulls access and WAF logs from Azure Front Door via Azure Monitor REST API. Confirm logs include client IP, HTTP status code, URL path, routing rule, and time-taken-ms.",
             "VP - Networking"),
            ("Azure Application Gateway Log Ingestion",
             "Verify that L7 Application Gateway access logs (HTTP method, URL, response code, backend latency) are collected and stored in the CloudGuard database.",
             "VP - Networking"),
            ("Azure API Management (APIM) Log Ingestion",
             "Confirm APIM gateway logs are ingested with fields such as API operation, response code, backend time, and subscription key identifier.",
             "VP - Networking"),
            ("Azure VM Diagnostic Log Ingestion",
             "Verify that Azure VM diagnostic / activity logs are collected from the configured VM resource ID.",
             "VP - Networking"),
            ("Real-Time Service Health Checks",
             "Validate that the Health Check module pings Front Door, App Gateway, APIM, App Service, Blob Storage, WAF, and Log Analytics endpoints in real time and shows HTTP status code, response time (ms), and healthy/unhealthy/unknown status.",
             "VP - Networking"),
            ("Infrastructure Flow Diagram",
             "Confirm the dashboard displays an interactive infrastructure topology diagram showing the flow: Front Door > App Gateway > APIM > App Service with live health indicators.",
             "VP - Networking"),
            ("Network Latency & Response Time Tracking",
             "Verify that log preprocessing extracts and normalises time_taken and backend latency fields, and that these are surfaced in analytics charts (e.g., Golden Signals - Latency).",
             "VP - Networking"),
        ],
    ),
    (
        "B. Cloud Operations & Platform (VP - Cloud)",
        [
            ("Azure Monitor REST API Integration",
             "Validate that the Log Collector agent authenticates via Azure AD Service Principal (Tenant ID, Client ID, Client Secret) and pulls activity logs from Azure Monitor for all configured resource IDs.",
             "VP - Cloud"),
            ("Azure PostgreSQL Database Connectivity",
             "Confirm the application connects to Azure Database for PostgreSQL (async via asyncpg) and that all tables (RawLog, CloudLog, Incident, AgentRun, RootCauseAnalysis, IncidentGroup) are created successfully on startup.",
             "VP - Cloud"),
            ("Automated Pipeline Scheduler",
             "Verify the APScheduler-based scheduler runs the 9-agent pipeline automatically every N hours (configurable via SCHEDULER_INTERVAL_HOURS). Confirm enable/disable toggle works.",
             "VP - Cloud"),
            ("Manual Pipeline Trigger",
             "Validate that the Run Pipeline button on the dashboard triggers the full 9-agent pipeline on demand and returns results.",
             "VP - Cloud"),
            ("Pipeline Enable / Disable Toggle",
             "Confirm the pipeline master switch (PIPELINE_ENABLED) can be toggled from the dashboard UI and the Settings page, and that a disabled pipeline skips scheduled runs.",
             "VP - Cloud"),
            ("Docker Compose Deployment",
             "Verify the application deploys successfully on an Azure VM using docker compose up -d with three containers: backend (FastAPI), frontend (React/Nginx), and Nginx reverse proxy.",
             "VP - Cloud"),
            ("Google Cloud Vertex AI (Gemini) Integration",
             "Confirm the Classification, RCA, Resolution, and Notification agents call Gemini 2.5 Flash via Vertex AI using the configured GCP Service Account Key.",
             "VP - Cloud"),
            ("Pipeline Run History & Audit Trail",
             "Verify that every pipeline run is logged in the AgentRun table with run ID, trigger type, start time, duration, logs processed, incidents created, P1/P2/P3 counts, emails sent, and status.",
             "VP - Cloud"),
            ("Log Analytics Workspace Integration",
             "Validate that the Azure Log Analytics Workspace ID is used for health checks and that the endpoint responds correctly.",
             "VP - Cloud"),
        ],
    ),
    (
        "C. Application & AI Pipeline (VP - Application)",
        [
            ("9-Agent LangGraph Pipeline Execution",
             "Verify the full pipeline executes all 9 agents in order: Log Collector > Preprocessing > Classification > RCA > Priority > Context > Resolution > Orchestrator > Notification.",
             "VP - Application"),
            ("Log Preprocessing & Deduplication",
             "Validate that the Preprocessing Engine cleans raw logs, normalises timestamps, extracts structured fields (level, category, source, resource ID), and removes duplicates.",
             "VP - Application"),
            ("AI-Powered Incident Classification (Gemini)",
             "Confirm the Classification Agent uses Gemini AI to detect incident type, intent, severity, and categorisation from preprocessed log data.",
             "VP - Application"),
            ("Root Cause Analysis (RCA) Agent",
             "Verify the RCA agent identifies probable root causes with confidence scores, collects evidence, matches historical incidents, and identifies affected components.",
             "VP - Application"),
            ("Priority Assignment (P1 / P2 / P3)",
             "Validate that the Priority Agent assigns correct priority levels: P1 (Critical), P2 (Warning), P3 (Informational). Verify priority justification is recorded.",
             "VP - Application"),
            ("Historical Context Lookup",
             "Confirm the Context Agent queries PostgreSQL for similar past incidents and surfaces historical resolution patterns.",
             "VP - Application"),
            ("AI-Powered Resolution Recommendations",
             "Verify the Resolution Agent generates actionable fix recommendations and runbooks using Gemini AI, including step-by-step remediation instructions.",
             "VP - Application"),
            ("Orchestrator Summary & Routing",
             "Confirm the Orchestrator Agent aggregates outputs from all previous agents, builds a pipeline summary, and routes notifications based on priority.",
             "VP - Application"),
            ("Incident Detail Panel (UI)",
             "Validate the incident detail panel shows: classification, priority justification, RCA with confidence score, historical context, AI-generated resolution, and runbook.",
             "VP - Application"),
            ("Real-Time WebSocket Updates",
             "Confirm the dashboard receives live pipeline progress updates via WebSocket: node_active, node_complete, pipeline_start, pipeline_complete, pipeline_error events.",
             "VP - Application"),
            ("Workflow Visualization (React Flow)",
             "Verify the Workflow View page displays the 9-agent pipeline as an interactive graph with animated node status transitions and real-time output result cards.",
             "VP - Application"),
            ("Dashboard KPI Cards",
             "Validate top-level KPI cards show: Total Incidents, Open Incidents, P1/P2/P3 counts, Resolved count, Avg Resolution Time, Emails Sent, and pipeline run status.",
             "VP - Application"),
            ("Analytics & Charting",
             "Verify the Analytics page displays: Incident Trend, Service Breakdown, Error Distribution, Notification History, Top Recurring Issues, MTTR, Golden Signals, Root Cause Distribution, and Resolution Metrics.",
             "VP - Application"),
            ("Log Explorer with Search & Filters",
             "Confirm the Log Explorer page provides paginated log viewing with filters for log level, source service, and free-text search.",
             "VP - Application"),
            ("Data Export (JSON / CSV / Excel)",
             "Validate that logs and incidents can be exported in JSON, CSV, and XLSX formats via the Export API and download buttons.",
             "VP - Application"),
            ("Incident Management (CRUD)",
             "Confirm incidents can be listed with pagination, filtered by priority/status/category/service, viewed in detail, and updated (e.g., mark as Resolved).",
             "VP - Application"),
        ],
    ),
    (
        "D. Security & Compliance (CISO)",
        [
            ("JWT Authentication & Protected API",
             "Verify that all API endpoints (except /api/auth/login) require a valid JWT Bearer token. Confirm login returns a signed JWT with 24-hour expiry.",
             "CISO"),
            ("Login / Logout Flow (UI)",
             "Validate the login page authenticates the user and redirects to the dashboard. Confirm logout clears the JWT token and redirects to login.",
             "CISO"),
            ("Protected Route Enforcement",
             "Confirm that unauthenticated users cannot access Dashboard, Analytics, Workflow, Log Explorer, or Settings pages.",
             "CISO"),
            ("WAF Log Monitoring",
             "Verify that WAF logs are ingested and WAF-blocked requests (403 status, rule violations) are classified as security incidents with appropriate priority.",
             "CISO"),
            ("SSL/TLS Certificate Error Detection",
             "Confirm the RCA agent detects SSL/TLS certificate errors (expired, mismatch, handshake failure) from log patterns and raises them as security-relevant incidents.",
             "CISO"),
            ("P1 Critical Incident Email Alerting",
             "Validate that P1 (Critical) incidents trigger immediate email notifications via the configured channel (SMTP / Azure Communication Service / Microsoft Graph API).",
             "CISO"),
            ("Priority-Based Notification Routing",
             "Confirm routing: P1 > Immediate email, P2 > Email digest, P3 > Dashboard only (no email).",
             "CISO"),
            ("Email Notification Audit (DB Records)",
             "Verify that every email sent is recorded in the database with: email_sent flag, email_sent_at timestamp, and email_recipient address.",
             "CISO"),
            ("CORS Policy Configuration",
             "Confirm CORS origins are restricted to configured allowed origins only and are not set to wildcard * in production.",
             "CISO"),
            ("Sensitive Credential Management",
             "Verify that all sensitive credentials are stored in .env file and not hardcoded in source code. Confirm .gitignore excludes .env and key files.",
             "CISO"),
        ],
    ),
    (
        "E. Cross-Functional / Overall System Validation",
        [
            ("End-to-End Pipeline Smoke Test",
             "Run the full pipeline end-to-end (manual trigger) and verify all 9 agents execute with expected output.",
             "All Stakeholders"),
            ("System Health API",
             "Verify the root endpoint (GET /) returns application name, version, and healthy status.",
             "All Stakeholders"),
            ("Dashboard Summary API",
             "Confirm GET /api/dashboard returns combined summary: raw log stats, processed log stats, incident counts, emails sent, avg resolution time, service breakdown, pipeline status.",
             "All Stakeholders"),
            ("Multi-Notification Channel Support",
             "Verify the notification system supports three channels: SMTP, Azure Communication Service, and Microsoft Graph API.",
             "All Stakeholders"),
            ("Responsive & Modern UI Design",
             "Confirm the React dashboard is responsive, includes sidebar navigation, header bar, dark-themed charts, animated counters, sparkline graphs, and smooth transitions.",
             "All Stakeholders"),
            ("Settings Page - Agent Status & History",
             "Verify the Settings page shows pipeline toggle, agent status, and pipeline run history with trigger type, counts, duration, and status.",
             "All Stakeholders"),
        ],
    ),
]


def create_pdf():
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "CloudGuard_Validation_Checklist.pdf"
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    elements = []

    # ── Title ──
    elements.append(Paragraph("CloudGuard - Stakeholder Validation Checklist", title_style))
    elements.append(Paragraph(
        f"Azure Incident Log Pipeline | Multi-Agent AI System for Banking Infrastructure | "
        f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 8))

    # ── Column widths (landscape A4 ~ 790pt usable) ──
    col_widths = [28, 130, 270, 80, 65, 72, 60, 85]

    # ── Headers ──
    headers = [
        Paragraph("S.No", header_style),
        Paragraph("Feature / Capability", header_style),
        Paragraph("Description & Validation Criteria", header_style),
        Paragraph("Relevant Stakeholder", header_style),
        Paragraph("Status<br/>(Pass/Fail/N/A)", header_style),
        Paragraph("Validated By", header_style),
        Paragraph("Validation Date", header_style),
        Paragraph("Remarks / Observations", header_style),
    ]

    all_data = [headers]
    row_types = ["header"]  # track row types for styling

    serial = 1
    for section_title, features in SECTIONS:
        # Section row (merged across all columns via spanning in style)
        section_row = [Paragraph(section_title, section_style), "", "", "", "", "", "", ""]
        all_data.append(section_row)
        row_types.append("section")

        for idx, (feature, description, stakeholder) in enumerate(features):
            row = [
                Paragraph(str(serial), body_center),
                Paragraph(feature, body_style),
                Paragraph(description, body_style),
                Paragraph(stakeholder, body_center),
                Paragraph("", body_center),
                Paragraph("", body_center),
                Paragraph("", body_center),
                Paragraph("", body_style),
            ]
            all_data.append(row)
            row_types.append("even" if idx % 2 == 0 else "odd")
            serial += 1

    # ── Build Table ──
    table = Table(all_data, colWidths=col_widths, repeatRows=1)

    # ── Table Style ──
    style_commands = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D0D0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    # Apply section and alternating row styles
    for i, row_type in enumerate(row_types):
        if row_type == "section":
            style_commands.append(("BACKGROUND", (0, i), (-1, i), MEDIUM_BLUE))
            style_commands.append(("TEXTCOLOR", (0, i), (-1, i), WHITE))
            style_commands.append(("SPAN", (0, i), (-1, i)))
        elif row_type == "odd":
            style_commands.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))

    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    # ── Page Break → Summary ──
    elements.append(PageBreak())
    elements.append(Paragraph("Validation Summary", title_style))
    elements.append(Spacer(1, 12))

    summary_data = [
        [Paragraph("Stakeholder Domain", header_style),
         Paragraph("Total Features", header_style),
         Paragraph("Validated (Pass)", header_style),
         Paragraph("Pending / Fail", header_style)],
        [Paragraph("VP - Networking", body_center), Paragraph("7", body_center), Paragraph("", body_center), Paragraph("", body_center)],
        [Paragraph("VP - Cloud", body_center), Paragraph("9", body_center), Paragraph("", body_center), Paragraph("", body_center)],
        [Paragraph("VP - Application", body_center), Paragraph("16", body_center), Paragraph("", body_center), Paragraph("", body_center)],
        [Paragraph("CISO", body_center), Paragraph("10", body_center), Paragraph("", body_center), Paragraph("", body_center)],
        [Paragraph("Cross-Functional", body_center), Paragraph("6", body_center), Paragraph("", body_center), Paragraph("", body_center)],
        [Paragraph("<b>TOTAL</b>", body_center), Paragraph("<b>48</b>", body_center), Paragraph("", body_center), Paragraph("", body_center)],
    ]

    summary_table = Table(summary_data, colWidths=[180, 120, 120, 120])
    summary_style = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D0D0")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BLUE),
    ]
    for i in range(2, len(summary_data) - 1, 2):
        summary_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
    summary_table.setStyle(TableStyle(summary_style))
    elements.append(summary_table)

    # ── Sign-Off Section ──
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Stakeholder Sign-Off", signoff_header))

    signoff_data = [
        [Paragraph("Stakeholder", header_style),
         Paragraph("Name", header_style),
         Paragraph("Signature / Approval", header_style),
         Paragraph("Date", header_style)],
        [Paragraph("VP - Networking", body_center), "", "", ""],
        [Paragraph("VP - Cloud", body_center), "", "", ""],
        [Paragraph("VP - Application", body_center), "", "", ""],
        [Paragraph("CISO", body_center), "", "", ""],
    ]
    signoff_table = Table(signoff_data, colWidths=[180, 140, 160, 100])
    signoff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D0D0")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(signoff_table)

    # ── Build PDF ──
    doc.build(elements)
    print(f"[OK] PDF created: {output_path}")
    print(f"   - 48 validation items across 5 stakeholder sections")
    print(f"   - Includes Summary + Sign-Off pages")


if __name__ == "__main__":
    create_pdf()

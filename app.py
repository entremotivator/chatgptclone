"""
Hud Security Interview Admin Suite

Admin Streamlit app with:
- auto-created Google Sheet + worksheets when missing
- auto-share of spreadsheet and Drive folders to entremotivator@gmail.com
- interviewer profile management
- interview archive and playback
- per-interviewer audio folders in Google Drive
- candidate prefill intake queue connected to the same sheet
"""

from __future__ import annotations

import io
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Hud Security Admin",
    page_icon="SG",
    layout="wide",
    initial_sidebar_state="expanded",
)


INTERVIEWER_HEADERS = [
    "Interviewer_ID",
    "Full_Name",
    "Email",
    "Role",
    "Phone",
    "Region",
    "Hiring_Manager",
    "Drive_Folder_ID",
    "Drive_Folder_Link",
    "Active",
    "Notes",
    "Created_At",
    "Updated_At",
]

PREFILL_HEADERS = [
    "Prefill_ID",
    "Created_At",
    "Submission_Status",
    "Candidate_First_Name",
    "Candidate_Last_Name",
    "Candidate_Email",
    "Candidate_Phone",
    "Candidate_City",
    "Candidate_State",
    "Position_Interest",
    "Preferred_Site",
    "Years_of_Experience",
    "Available_Shifts",
    "Reliable_Transportation",
    "Guard_Card_Status",
    "Firearm_Permit_Status",
    "CPR_Certified",
    "First_Aid_Certified",
    "Can_Pass_Background_Check",
    "Can_Pass_Drug_Test",
    "Start_Availability",
    "Candidate_Summary",
    "Prefill_Answers_JSON",
    "Source_App",
]

INTERVIEW_HEADERS = [
    "Interview_ID",
    "Created_At",
    "Prefill_ID",
    "Interview_Date",
    "Interview_Time",
    "Follow_Up_Date",
    "Interviewer_ID",
    "Interviewer_Name",
    "Interviewer_Email",
    "Interviewer_Role",
    "Interviewer_Region",
    "Candidate_First_Name",
    "Candidate_Last_Name",
    "Candidate_Email",
    "Candidate_Phone",
    "Candidate_City",
    "Candidate_State",
    "Position_Applying_For",
    "Site_Assignment",
    "Years_of_Experience",
    "Available_Shifts",
    "Reliable_Transportation",
    "Guard_Card_Status",
    "Firearm_Permit_Status",
    "CPR_Certified",
    "First_Aid_Certified",
    "Can_Pass_Background_Check",
    "Can_Pass_Drug_Test",
    "Behavior_Score",
    "Question_Score",
    "Scenario_Score",
    "Final_Interview_Score",
    "Hiring_Recommendation",
    "Hiring_Status",
    "Scenario_Name",
    "Scenario_Response",
    "Strengths",
    "Areas_for_Development",
    "Candidate_Summary",
    "Interviewer_Notes",
    "Internal_HR_Notes",
    "Prefill_Answers_JSON",
    "Question_Answers_JSON",
    "Question_Scores_JSON",
    "Audio_File_ID",
    "Audio_File_Name",
    "Audio_Mime_Type",
    "Audio_Drive_Link",
    "Audio_Duration_Seconds",
    "Audio_Status",
]

POSITIONS = [
    "Unarmed Security Guard",
    "Armed Security Officer",
    "Patrol Officer",
    "Site Supervisor",
    "Loss Prevention",
    "Event Security",
    "Mobile Patrol",
    "Dispatcher",
]

SHIFT_OPTIONS = [
    "Morning (6AM-2PM)",
    "Afternoon (2PM-10PM)",
    "Night (10PM-6AM)",
    "Overnight",
    "Weekends",
    "Holidays",
    "On-Call",
]

EXPERIENCE_OPTIONS = [
    "No Experience",
    "Less than 1 Year",
    "1-2 Years",
    "3-5 Years",
    "5-10 Years",
    "10+ Years",
]

INTERVIEW_QUESTIONS = [
    ("Q1", "Tell us about your previous security experience and what you learned from it.", "Experience"),
    ("Q2", "What certifications, licenses, or specialized training do you currently hold for this role?", "Experience"),
    ("Q3", "Describe the most challenging site or post you have worked and how you handled it.", "Experience"),
    ("Q4", "Describe a specific situation where you successfully de-escalated a confrontation.", "De-escalation"),
    ("Q5", "A client becomes verbally abusive and demanding. How do you keep control of the interaction?", "De-escalation"),
    ("Q6", "What does customer service mean in a security role, and how do you balance service with enforcement?", "De-escalation"),
    ("Q7", "How do you communicate with people from different backgrounds or with language barriers?", "De-escalation"),
    ("Q8", "Walk me through your first steps when responding to a reported theft in progress.", "Operations"),
    ("Q9", "How do you stay alert during a 12-hour overnight shift?", "Operations"),
    ("Q10", "How would you handle an unauthorized person attempting to access a restricted area?", "Operations"),
    ("Q11", "What are your priorities in the first 3 minutes of a building fire emergency?", "Operations"),
    ("Q12", "How do you write a strong incident report and what details can never be skipped?", "Operations"),
    ("Q13", "How do you handle a medical emergency when you are the first responder on scene?", "Operations"),
    ("Q14", "What would you do if you discovered a suspicious unattended package?", "Operations"),
    ("Q15", "Describe your patrol methodology and how you keep it unpredictable but effective.", "Operations"),
    ("Q16", "What would you do if you witnessed a fellow officer violating policy or acting unethically?", "Judgment"),
    ("Q17", "Describe a time you made a quick judgment call under pressure. What happened?", "Judgment"),
    ("Q18", "How do you coordinate with law enforcement during a serious incident on your post?", "Judgment"),
    ("Q19", "What do you do if a supervisor instructs you to violate protocol or the law?", "Judgment"),
    ("Q20", "How do you decide whether a situation needs immediate action or should be monitored and reported?", "Judgment"),
    ("Q21", "What security technology have you used: CCTV, visitor systems, access control, patrol tools, or radios?", "Technology"),
    ("Q22", "How do you hand off a post at the end of a shift so the next officer is set up for success?", "Technology"),
    ("Q23", "How do you stay current with security best practices, regulations, and site requirements?", "Professionalism"),
    ("Q24", "Describe a time you received critical feedback. How did you respond and what changed?", "Professionalism"),
    ("Q25", "Why are you pursuing private security, and where do you want to grow in the next 3 years?", "Professionalism"),
]

INCIDENT_SCENARIOS = {
    "Fire Emergency": {
        "prompt": "A fire alarm activates, you smell smoke on the third floor, and employees are panicking. Elevators are still in use. What are your exact steps?",
        "ideal_points": [
            "Call emergency services immediately",
            "Direct everyone to stairwells and away from elevators",
            "Clear and secure the affected zone",
            "Report smoke location and hazards",
            "Brief responders clearly when they arrive",
        ],
    },
    "Active Threat": {
        "prompt": "A person enters the lobby acting erratically, shouting threats, and refusing to leave. No visible weapon yet. You are alone. What do you do?",
        "ideal_points": [
            "Create distance and protect bystanders",
            "Call dispatch or emergency support immediately",
            "Use verbal control and de-escalation",
            "Avoid unnecessary physical contact",
            "Control the flow of people into the area",
        ],
    },
    "Medical Emergency": {
        "prompt": "You find an employee unconscious near their workstation. They are not responding and there are no visible injuries. What are your immediate actions?",
        "ideal_points": [
            "Call 911 immediately",
            "Check responsiveness and breathing",
            "Begin CPR if trained and necessary",
            "Send someone to guide EMS in",
            "Protect the scene and the person's dignity",
        ],
    },
    "Suspicious Package": {
        "prompt": "A package with no label is found in the lobby. No deliveries were expected and it appears unusual. How do you respond?",
        "ideal_points": [
            "Do not touch or move it",
            "Clear the area calmly",
            "Set a perimeter and notify authorities",
            "Document witnesses and timing",
            "Await official clearance",
        ],
    },
    "Unauthorized Access": {
        "prompt": "A person is found in a restricted server room after hours. They claim to be a contractor but have no badge and no one can verify them. What do you do?",
        "ideal_points": [
            "Control and escort them out calmly",
            "Verify identity and reason for presence",
            "Notify IT or site leadership",
            "Keep them supervised",
            "Document the incident fully",
        ],
    },
}


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            --sg-ink: #8f6d23;
            --sg-soft: #9e7b2f;
            --sg-border: #e6ddd1;
            --sg-panel: rgba(255,255,255,0.84);
            --sg-brand: #183447;
            --sg-gold: #aa7b26;
            --sg-gold-soft: #f6edd9;
            --sg-good: #166534;
            --sg-warn: #9a6700;
            --sg-bad: #9f1239;
        }

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
            color: var(--sg-ink) !important;
        }

        p, span, div, li, label, small, strong, td, th {
            color: var(--sg-ink);
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stTextInputRootElement"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stSelectbox"] *,
        [data-testid="stMultiSelect"] *,
        [data-testid="stRadio"] *,
        [data-testid="stCheckbox"] *,
        [data-testid="stFileUploader"] *,
        [data-testid="stAudioInput"] *,
        .stButton button,
        .stDownloadButton button {
            color: var(--sg-gold) !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #b6944b !important;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top right, rgba(170, 123, 38, 0.12), transparent 24%),
                radial-gradient(circle at left top, rgba(24, 52, 71, 0.10), transparent 30%),
                linear-gradient(180deg, #faf6ee 0%, #fcfbf8 24%, #ffffff 100%);
        }

        h1, h2, h3, .shield-brand {
            font-family: 'Space Grotesk', sans-serif !important;
            letter-spacing: -0.03em;
        }

        h2, h3, strong, .gold-text {
            color: var(--sg-gold);
            font-weight: 800;
        }

        .shield-hero {
            background: linear-gradient(135deg, #122f43 0%, #1d415a 62%, #87621d 150%);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 26px;
            padding: 28px 30px;
            margin-bottom: 18px;
            box-shadow: 0 20px 56px rgba(18, 47, 67, 0.15);
        }

        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 11px;
            font-weight: 800;
            color: rgba(255,255,255,0.75);
            margin-bottom: 8px;
        }

        .hero-title {
            font-size: 40px;
            font-weight: 800;
            line-height: 1.04;
            margin: 0 0 8px 0;
            color: #fff !important;
        }

        .hero-subtitle {
            font-size: 15px;
            line-height: 1.6;
            color: rgba(255,255,255,0.82);
            max-width: 900px;
        }

        .shield-hero *, .shield-hero div, .shield-hero span {
            color: #fff !important;
        }

        .metric-shell {
            background: var(--sg-panel);
            border: 1px solid var(--sg-border);
            border-radius: 18px;
            padding: 18px;
            min-height: 120px;
            box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
        }

        .metric-label {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 11px;
            font-weight: 800;
            color: var(--sg-soft);
        }

        .metric-value {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 34px;
            font-weight: 700;
            color: var(--sg-gold);
            margin-top: 8px;
        }

        .metric-note {
            color: var(--sg-soft);
            font-size: 13px;
            margin-top: 4px;
        }

        .section-panel {
            background: var(--sg-panel);
            border: 1px solid var(--sg-border);
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 8px 24px rgba(17, 24, 39, 0.03);
        }

        .question-card {
            border: 1px solid var(--sg-border);
            border-left: 4px solid var(--sg-gold);
            border-radius: 14px;
            background: rgba(255,255,255,0.92);
            padding: 15px 16px 8px 16px;
            margin-bottom: 10px;
        }

        .question-meta {
            text-transform: uppercase;
            letter-spacing: 0.10em;
            font-size: 11px;
            font-weight: 800;
            color: var(--sg-soft);
            margin-bottom: 8px;
        }

        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .status-good { background: #dcfce7; color: var(--sg-good); }
        .status-warn { background: #fef3c7; color: var(--sg-warn); }
        .status-bad { background: #fee2e2; color: var(--sg-bad); }
        .status-neutral { background: #e5e7eb; color: #374151; }

        .sidebar-mark {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 24px;
            font-weight: 700;
            color: var(--sg-gold);
            margin-bottom: 2px;
        }

        .sidebar-submark {
            font-size: 11px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--sg-soft);
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="shield-hero">
            <div class="eyebrow">Hud Security Interview System</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-shell">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_secret(key: str, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    return cleaned.strip("-") or "record"


def safe_json_loads(value):
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


def status_pill(label: str, style: str) -> str:
    return f'<span class="status-pill status-{style}">{label}</span>'


def score_to_recommendation(score: float) -> str:
    if score >= 88:
        return "Strong Hire"
    if score >= 76:
        return "Hire"
    if score >= 62:
        return "Maybe"
    return "Do Not Hire"


def app_root() -> Path:
    return Path(__file__).resolve().parent


def local_config_path() -> Path:
    return app_root() / ".streamlit" / "local_state.json"


def load_local_config() -> dict:
    path = local_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_local_config(payload: dict) -> None:
    path = local_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def configured_share_email() -> str:
    return str(safe_secret("default_share_email", "entremotivator@gmail.com")).strip() or "entremotivator@gmail.com"


def configured_sheet_title() -> str:
    return str(safe_secret("gsheet_name", "Hud Security Interview Hub")).strip() or "Hud Security Interview Hub"


def configured_admin_username() -> str:
    return str(safe_secret("admin_username", "admin")).strip() or "admin"


def configured_admin_password() -> str:
    return str(safe_secret("admin_password", "")).strip()


def ensure_admin_auth() -> None:
    expected_password = configured_admin_password()
    if not expected_password:
        return
    if st.session_state.get("hud_security_admin_authed"):
        return

    render_hero(
        "Admin Access Required",
        "This full Hud Security admin workspace is password protected. Use the admin credentials stored in Streamlit secrets to unlock the dashboard.",
    )
    st.markdown(
        """
        <div class="section-panel">
            <strong>Secure Admin Login</strong><br>
            This protects interviewer profiles, live interview records, Google Drive audio access, and admin-only reporting.
        </div>
        """,
        unsafe_allow_html=True,
    )
    username = st.text_input("Admin username")
    password = st.text_input("Admin password", type="password")
    if st.button("Unlock Admin", type="primary", use_container_width=True):
        if username.strip() == configured_admin_username() and password == expected_password:
            st.session_state["hud_security_admin_authed"] = True
            st.rerun()
        st.error("Incorrect admin username or password.")
    st.stop()


@st.cache_resource(show_spinner=False)
def get_google_clients():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return {
            "sheets": gspread.authorize(creds),
            "drive": build("drive", "v3", credentials=creds, cache_discovery=False),
        }
    except Exception:
        return {"sheets": None, "drive": None}


def share_file_with_email(file_id: str, email: str, role: str = "writer") -> None:
    drive_service = get_google_clients()["drive"]
    if drive_service is None or not file_id or not email:
        return
    try:
        drive_service.permissions().create(
            fileId=file_id,
            body={
                "type": "user",
                "role": role,
                "emailAddress": email,
            },
            sendNotificationEmail=False,
        ).execute()
    except Exception:
        pass


def locate_existing_spreadsheet_by_name(title: str) -> tuple[str, str]:
    drive_service = get_google_clients()["drive"]
    if drive_service is None:
        return "", ""
    safe_title = title.replace("'", "\\'")
    try:
        result = drive_service.files().list(
            q=f"mimeType='application/vnd.google-apps.spreadsheet' and trashed=false and name='{safe_title}'",
            spaces="drive",
            pageSize=1,
            fields="files(id, webViewLink)",
        ).execute()
        files = result.get("files", [])
        if not files:
            return "", ""
        file_id = files[0].get("id", "")
        return file_id, files[0].get("webViewLink", "")
    except Exception:
        return "", ""


def ensure_spreadsheet():
    client = get_google_clients()["sheets"]
    if client is None:
        return None

    local_state = load_local_config()
    spreadsheet_url = str(safe_secret("gsheet_url", "")).strip() or local_state.get("gsheet_url", "")

    if spreadsheet_url:
        try:
            sheet = client.open_by_url(spreadsheet_url)
            return sheet
        except Exception:
            pass

    title = configured_sheet_title()
    existing_id, existing_link = locate_existing_spreadsheet_by_name(title)
    if existing_id:
        try:
            sheet = client.open_by_key(existing_id)
            save_local_config(
                {
                    **local_state,
                    "gsheet_url": sheet.url,
                    "spreadsheet_id": existing_id,
                    "spreadsheet_link": existing_link or sheet.url,
                }
            )
            share_file_with_email(existing_id, configured_share_email())
            return sheet
        except Exception:
            pass

    try:
        sheet = client.create(title)
        share_file_with_email(sheet.id, configured_share_email())
        save_local_config(
            {
                **local_state,
                "gsheet_url": sheet.url,
                "spreadsheet_id": sheet.id,
                "spreadsheet_link": sheet.url,
            }
        )
        return sheet
    except Exception:
        return None


def get_spreadsheet():
    return ensure_spreadsheet()


def get_audio_parent_folder_id() -> str:
    explicit = str(safe_secret("drive_parent_folder_id", "")).strip()
    if explicit:
        share_file_with_email(explicit, configured_share_email())
        return explicit

    local_state = load_local_config()
    cached = str(local_state.get("audio_parent_folder_id", "")).strip()
    if cached:
        share_file_with_email(cached, configured_share_email())
        return cached

    drive_service = get_google_clients()["drive"]
    if drive_service is None:
        return ""

    folder_name = str(safe_secret("audio_root_folder_name", "Hud Security Interview Audio")).strip() or "Hud Security Interview Audio"
    safe_folder_name = folder_name.replace("'", "\\'")
    try:
        existing = drive_service.files().list(
            q=f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{safe_folder_name}'",
            spaces="drive",
            pageSize=1,
            fields="files(id, webViewLink)",
        ).execute()
        files = existing.get("files", [])
        if files:
            folder_id = files[0].get("id", "")
            share_file_with_email(folder_id, configured_share_email())
            save_local_config({**local_state, "audio_parent_folder_id": folder_id})
            return folder_id

        created = drive_service.files().create(
            body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id, webViewLink",
        ).execute()
        folder_id = created.get("id", "")
        share_file_with_email(folder_id, configured_share_email())
        save_local_config({**local_state, "audio_parent_folder_id": folder_id})
        return folder_id
    except Exception:
        return ""


def ensure_worksheet(title: str, headers: list[str]):
    spreadsheet = get_spreadsheet()
    if spreadsheet is None:
        return None

    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(40, len(headers) + 10))
        worksheet.update([headers], "A1")
        return worksheet

    existing_headers = worksheet.row_values(1)
    if not existing_headers:
        worksheet.update([headers], "A1")
        return worksheet

    merged = existing_headers[:]
    for header in headers:
        if header not in merged:
            merged.append(header)
    if merged != existing_headers:
        worksheet.update([merged], "A1")
    return worksheet


def load_records(title: str, headers: list[str]) -> list[dict]:
    worksheet = ensure_worksheet(title, headers)
    if worksheet is None:
        return []
    try:
        return worksheet.get_all_records()
    except Exception:
        return []


def append_record(title: str, headers: list[str], record: dict) -> bool:
    worksheet = ensure_worksheet(title, headers)
    if worksheet is None:
        return False
    try:
        current_headers = worksheet.row_values(1)
        row = [str(record.get(header, "")) for header in current_headers]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False


def upsert_interviewer(profile: dict) -> bool:
    worksheet = ensure_worksheet("Interviewers", INTERVIEWER_HEADERS)
    if worksheet is None:
        return False

    try:
        headers = worksheet.row_values(1)
        records = worksheet.get_all_records()
        row_index = None
        profile_id = str(profile.get("Interviewer_ID", "")).strip()
        profile_email = str(profile.get("Email", "")).strip().lower()

        for idx, record in enumerate(records, start=2):
            existing_id = str(record.get("Interviewer_ID", "")).strip()
            existing_email = str(record.get("Email", "")).strip().lower()
            if profile_id and existing_id == profile_id:
                row_index = idx
                break
            if profile_email and existing_email == profile_email:
                row_index = idx
                break

        values = [str(profile.get(header, "")) for header in headers]
        if row_index is None:
            worksheet.append_row(values, value_input_option="USER_ENTERED")
        else:
            worksheet.update([values], f"A{row_index}")
        return True
    except Exception:
        return False


def drive_enabled() -> bool:
    return get_google_clients()["drive"] is not None


def build_drive_folder_name(profile: dict) -> str:
    name = str(profile.get("Full_Name", "")).strip() or "Interviewer"
    return f"Hud-Security-Audio-{sanitize_name(name)}"


def find_or_create_drive_folder(folder_name: str, parent_id: str = "") -> tuple[str, str]:
    drive_service = get_google_clients()["drive"]
    if drive_service is None:
        return "", ""

    safe_name = folder_name.replace("'", "\\'")
    query_parts = [
        "mimeType='application/vnd.google-apps.folder'",
        "trashed=false",
        f"name='{safe_name}'",
    ]
    if parent_id:
        query_parts.append(f"'{parent_id}' in parents")

    try:
        result = drive_service.files().list(
            q=" and ".join(query_parts),
            spaces="drive",
            pageSize=1,
            fields="files(id, webViewLink)",
        ).execute()
        files = result.get("files", [])
        if files:
            folder_id = files[0].get("id", "")
            share_file_with_email(folder_id, configured_share_email())
            return folder_id, files[0].get("webViewLink", "")

        body = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            body["parents"] = [parent_id]
        created = drive_service.files().create(body=body, fields="id, webViewLink").execute()
        folder_id = created.get("id", "")
        share_file_with_email(folder_id, configured_share_email())
        return folder_id, created.get("webViewLink", "")
    except Exception:
        return "", ""


def upload_audio_to_drive(audio_bytes: bytes, mime_type: str, filename: str, interviewer_profile: dict) -> dict:
    drive_service = get_google_clients()["drive"]
    if drive_service is None or not audio_bytes:
        return {"ok": False, "message": "Drive service not available."}

    try:
        from googleapiclient.http import MediaIoBaseUpload

        folder_id = interviewer_profile.get("Drive_Folder_ID", "")
        folder_link = interviewer_profile.get("Drive_Folder_Link", "")
        if not folder_id:
            folder_id, folder_link = find_or_create_drive_folder(
                build_drive_folder_name(interviewer_profile),
                get_audio_parent_folder_id(),
            )

        metadata = {"name": filename}
        if folder_id:
            metadata["parents"] = [folder_id]

        created = drive_service.files().create(
            body=metadata,
            media_body=MediaIoBaseUpload(io.BytesIO(audio_bytes), mimetype=mime_type, resumable=False),
            fields="id, name, mimeType, webViewLink, size",
        ).execute()
        file_id = created.get("id", "")
        share_file_with_email(file_id, configured_share_email())

        return {
            "ok": True,
            "folder_id": folder_id,
            "folder_link": folder_link,
            "file_id": file_id,
            "file_name": created.get("name", filename),
            "mime_type": created.get("mimeType", mime_type),
            "drive_link": created.get("webViewLink", ""),
            "size": created.get("size", ""),
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


@st.cache_data(show_spinner=False, ttl=120)
def download_drive_audio(file_id: str) -> bytes:
    drive_service = get_google_clients()["drive"]
    if drive_service is None or not file_id:
        return b""
    try:
        from googleapiclient.http import MediaIoBaseDownload

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, drive_service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()
    except Exception:
        return b""


def render_audio_capture() -> dict:
    st.markdown("#### Interview Audio")
    st.caption("Use live mic capture when available. If the browser build does not support that input, upload the recording file instead.")

    audio_file = None
    if hasattr(st, "audio_input"):
        audio_file = st.audio_input("Record interview audio", key="admin_interview_audio")
    if audio_file is None:
        audio_file = st.file_uploader(
            "Upload interview audio",
            type=["wav", "mp3", "m4a", "ogg", "mpeg", "mp4"],
            key="admin_interview_audio_uploader",
        )
    if audio_file is None:
        return {}

    payload = {
        "bytes": audio_file.getvalue(),
        "name": getattr(audio_file, "name", "") or f"interview-{uuid.uuid4().hex[:8]}.wav",
        "mime_type": getattr(audio_file, "type", "") or "audio/wav",
        "duration_seconds": "",
    }
    st.audio(payload["bytes"], format=payload["mime_type"])
    return payload


def load_interviewers_df() -> pd.DataFrame:
    df = pd.DataFrame(load_records("Interviewers", INTERVIEWER_HEADERS))
    if df.empty:
        return pd.DataFrame(columns=INTERVIEWER_HEADERS + ["Label"])
    for column in INTERVIEWER_HEADERS:
        if column not in df.columns:
            df[column] = ""
    df["Active"] = df["Active"].astype(str).replace({"TRUE": "Yes", "FALSE": "No"})
    df["Label"] = df["Full_Name"].fillna("") + " | " + df["Role"].fillna("")
    return df


def load_prefill_df() -> pd.DataFrame:
    df = pd.DataFrame(load_records("Prefill_Responses", PREFILL_HEADERS))
    if df.empty:
        return pd.DataFrame(columns=PREFILL_HEADERS + ["Candidate_Name", "Label"])
    for column in PREFILL_HEADERS:
        if column not in df.columns:
            df[column] = ""
    df["Candidate_Name"] = (
        df["Candidate_First_Name"].fillna("").str.strip() + " " + df["Candidate_Last_Name"].fillna("").str.strip()
    ).str.strip()
    df["Label"] = (
        df["Candidate_Name"].fillna("")
        + " | "
        + df["Position_Interest"].fillna("")
        + " | "
        + df["Created_At"].fillna("")
    )
    return df


def load_interviews_df() -> pd.DataFrame:
    df = pd.DataFrame(load_records("Interviews", INTERVIEW_HEADERS))
    if df.empty:
        return pd.DataFrame(columns=INTERVIEW_HEADERS + ["Candidate_Name", "Has_Audio"])
    for column in INTERVIEW_HEADERS:
        if column not in df.columns:
            df[column] = ""
    for column in ["Behavior_Score", "Question_Score", "Scenario_Score", "Final_Interview_Score", "Audio_Duration_Seconds"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["Candidate_Name"] = (
        df["Candidate_First_Name"].fillna("").str.strip() + " " + df["Candidate_Last_Name"].fillna("").str.strip()
    ).str.strip()
    df["Has_Audio"] = df["Audio_File_ID"].fillna("").astype(str).str.len() > 0
    return df


def connection_summary() -> dict:
    spreadsheet = get_spreadsheet()
    local_state = load_local_config()
    return {
        "sheets": spreadsheet is not None,
        "drive": drive_enabled(),
        "audio_input": hasattr(st, "audio_input"),
        "share_email": configured_share_email(),
        "spreadsheet_link": local_state.get("spreadsheet_link") or local_state.get("gsheet_url", ""),
    }


def render_recent_interviews(df: pd.DataFrame) -> None:
    st.markdown("### Recent Interviews")
    if df.empty:
        st.info("No interviews saved yet.")
        return
    recent = df.sort_values("Created_At", ascending=False).head(8)
    for _, row in recent.iterrows():
        score = row.get("Final_Interview_Score")
        score_text = "No score" if pd.isna(score) else f"{score:.1f}"
        st.markdown(
            f"""
            <div class="section-panel">
                <strong>{row.get("Candidate_Name", "Unnamed Candidate")}</strong><br>
                <span style="color:#5e6775;font-size:13px">
                    {row.get("Position_Applying_For", "Unknown Position")} · {row.get("Interviewer_Name", "Unassigned")} · Score {score_text} · {row.get("Hiring_Recommendation", "")}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_dashboard(interviews_df: pd.DataFrame, interviewers_df: pd.DataFrame, prefill_df: pd.DataFrame) -> None:
    render_hero(
        "Hiring Command Center",
        "Admin dashboard with soft gold emphasis, automatic Google workspace setup, interviewer-owned audio folders, and a linked candidate prefill queue.",
    )

    active_interviewers = 0 if interviewers_df.empty else len(interviewers_df[interviewers_df["Active"].astype(str).str.lower().isin(["yes", "true", "1"])])
    avg_score = "0.0"
    if not interviews_df.empty and interviews_df["Final_Interview_Score"].notna().any():
        avg_score = f"{interviews_df['Final_Interview_Score'].mean():.1f}"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Total Interviews", str(len(interviews_df)), "Saved in the shared Google Sheet")
    with c2:
        render_metric("Prefill Intake", str(len(prefill_df)), "Candidate questionnaire submissions")
    with c3:
        render_metric("Active Interviewers", str(active_interviewers), "Profiles with folder ownership ready")
    with c4:
        render_metric("Average Score", avg_score, "Composite interview score")

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### Recommendation Mix")
        if interviews_df.empty:
            st.info("Interview submissions will appear here.")
        else:
            st.bar_chart(interviews_df["Hiring_Recommendation"].value_counts())

        st.markdown("### Intake to Interview Conversion")
        if prefill_df.empty and interviews_df.empty:
            st.info("No candidate pipeline records yet.")
        else:
            pipeline = pd.Series(
                {
                    "Prefill Submitted": len(prefill_df),
                    "Interview Completed": len(interviews_df),
                }
            )
            st.bar_chart(pipeline)

    with right:
        st.markdown("### System Readiness")
        conn = connection_summary()
        st.markdown(
            f"""
            <div class="section-panel">
                <p>{status_pill('Sheets Ready', 'good') if conn['sheets'] else status_pill('Sheets Missing', 'bad')}</p>
                <p>{status_pill('Drive Ready', 'good') if conn['drive'] else status_pill('Drive Missing', 'warn')}</p>
                <p>{status_pill('Mic Capture Ready', 'good') if conn['audio_input'] else status_pill('Upload Fallback', 'neutral')}</p>
                <p><strong>Auto-share email:</strong> {conn['share_email']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Audio Coverage")
        if interviews_df.empty:
            st.info("Audio coverage appears once interviews are saved.")
        else:
            coverage = pd.Series(
                {
                    "With Audio": int(interviews_df["Has_Audio"].sum()),
                    "Without Audio": int((~interviews_df["Has_Audio"]).sum()),
                }
            )
            st.bar_chart(coverage)

    render_recent_interviews(interviews_df)


def render_interviewer_profiles(interviewers_df: pd.DataFrame) -> None:
    render_hero(
        "Interviewer Profiles",
        "Each interviewer can own a dedicated Google Drive audio folder. New folders are created automatically and shared to the admin email.",
    )

    options = ["Create New Profile"]
    if not interviewers_df.empty:
        options.extend(interviewers_df["Label"].fillna("").tolist())

    selected_label = st.selectbox("Profile to edit", options)
    selected = {}
    if selected_label != "Create New Profile" and not interviewers_df.empty:
        matches = interviewers_df[interviewers_df["Label"] == selected_label]
        if not matches.empty:
            selected = matches.iloc[0].to_dict()

    left, right = st.columns([1.2, 1])
    with left:
        full_name = st.text_input("Full name *", value=selected.get("Full_Name", ""))
        email = st.text_input("Email *", value=selected.get("Email", ""))
        role = st.text_input("Role", value=selected.get("Role", "Lead Interviewer"))
        phone = st.text_input("Phone", value=selected.get("Phone", ""))
        region = st.text_input("Region", value=selected.get("Region", ""))
        manager = st.text_input("Hiring manager", value=selected.get("Hiring_Manager", ""))
        notes = st.text_area("Notes", value=selected.get("Notes", ""), height=120)
        active = st.toggle("Active interviewer", value=str(selected.get("Active", "Yes")).lower() in ["yes", "true", "1"])
        make_folder = st.checkbox("Auto-create or refresh Drive folder", value=not bool(selected.get("Drive_Folder_ID", "")))

        if st.button("Save interviewer profile", type="primary", use_container_width=True):
            if not full_name.strip() or not email.strip():
                st.error("Full name and email are required.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                profile = {
                    "Interviewer_ID": selected.get("Interviewer_ID") or f"IVR-{uuid.uuid4().hex[:8].upper()}",
                    "Full_Name": full_name.strip(),
                    "Email": email.strip(),
                    "Role": role.strip(),
                    "Phone": phone.strip(),
                    "Region": region.strip(),
                    "Hiring_Manager": manager.strip(),
                    "Drive_Folder_ID": selected.get("Drive_Folder_ID", ""),
                    "Drive_Folder_Link": selected.get("Drive_Folder_Link", ""),
                    "Active": "Yes" if active else "No",
                    "Notes": notes.strip(),
                    "Created_At": selected.get("Created_At") or now,
                    "Updated_At": now,
                }
                if make_folder and drive_enabled():
                    folder_id, folder_link = find_or_create_drive_folder(build_drive_folder_name(profile), get_audio_parent_folder_id())
                    if folder_id:
                        profile["Drive_Folder_ID"] = folder_id
                        profile["Drive_Folder_Link"] = folder_link

                if upsert_interviewer(profile):
                    st.success("Interviewer profile saved.")
                    st.rerun()
                else:
                    st.error("Could not save the interviewer profile.")

    with right:
        st.markdown("### Current Directory")
        if interviewers_df.empty:
            st.info("No interviewer profiles yet.")
        else:
            st.dataframe(
                interviewers_df[["Full_Name", "Email", "Role", "Region", "Active", "Drive_Folder_ID"]],
                use_container_width=True,
                hide_index=True,
            )
        st.markdown(
            """
            <div class="section-panel">
                <strong>How this works</strong><br>
                New interviewer folders go under the shared audio root automatically, then recordings upload into that interviewer's folder.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_prefill_queue(prefill_df: pd.DataFrame) -> None:
    render_hero(
        "Candidate Prefill Queue",
        "This queue comes from the standalone Hud Security candidate questionnaire. Interviewers can start with richer prefilled candidate details before the live interview begins.",
    )

    if prefill_df.empty:
        st.info("No questionnaire submissions yet.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        search = st.text_input("Search candidate")
    with c2:
        status_filter = st.selectbox("Submission status", ["All"] + sorted(prefill_df["Submission_Status"].dropna().astype(str).unique().tolist()))
    with c3:
        position_filter = st.selectbox("Position", ["All"] + sorted(prefill_df["Position_Interest"].dropna().astype(str).unique().tolist()))

    filtered = prefill_df.copy()
    if search.strip():
        filtered = filtered[filtered["Candidate_Name"].str.contains(search, case=False, na=False)]
    if status_filter != "All":
        filtered = filtered[filtered["Submission_Status"] == status_filter]
    if position_filter != "All":
        filtered = filtered[filtered["Position_Interest"] == position_filter]

    st.dataframe(
        filtered[
            [
                "Prefill_ID",
                "Candidate_Name",
                "Candidate_Email",
                "Position_Interest",
                "Years_of_Experience",
                "Submission_Status",
                "Created_At",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    selected_id = st.selectbox("Open prefill record", filtered["Prefill_ID"].tolist())
    selected = filtered[filtered["Prefill_ID"] == selected_id].iloc[0].to_dict()
    answers = safe_json_loads(selected.get("Prefill_Answers_JSON", "{}"))

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("### Candidate Snapshot")
        st.markdown(
            f"""
            <div class="section-panel">
                <strong>{selected.get('Candidate_Name', '')}</strong><br>
                <span style="color:#5e6775;font-size:13px">
                    {selected.get('Position_Interest', '')} · {selected.get('Candidate_Email', '')} · {selected.get('Candidate_Phone', '')}
                </span><br><br>
                <strong>Experience:</strong> {selected.get('Years_of_Experience', '')}<br>
                <strong>Shifts:</strong> {selected.get('Available_Shifts', '')}<br>
                <strong>Transport:</strong> {selected.get('Reliable_Transportation', '')}<br>
                <strong>Status:</strong> {selected.get('Submission_Status', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write(selected.get("Candidate_Summary", "") or "No summary submitted.")

    with right:
        st.markdown("### Prefill Answers")
        for question_id, question_text, category in INTERVIEW_QUESTIONS[:10]:
            with st.expander(f"{question_id} · {category}", expanded=False):
                st.write(question_text)
                st.write(answers.get(question_id, "") or "No answer captured.")


def render_new_interview(interviewers_df: pd.DataFrame, prefill_df: pd.DataFrame) -> None:
    render_hero(
        "Conduct Interview",
        "Choose an interviewer, optionally import a candidate prefill submission, record audio, and save the interview into the shared archive with Drive playback support.",
    )

    prefill_lookup = {"No Prefill": {}}
    if not prefill_df.empty:
        for _, row in prefill_df.iterrows():
            prefill_lookup[row["Label"]] = row.to_dict()

    prefill_choice = st.selectbox("Candidate prefill to import", list(prefill_lookup.keys()))
    prefill = prefill_lookup[prefill_choice]
    prefill_answers = safe_json_loads(prefill.get("Prefill_Answers_JSON", "{}"))

    st.markdown("### Session Owner")
    active_profiles = interviewers_df[interviewers_df["Active"].astype(str).str.lower().isin(["yes", "true", "1"])] if not interviewers_df.empty else interviewers_df
    interviewer_lookup = {"Manual Entry": None}
    if not active_profiles.empty:
        for _, row in active_profiles.iterrows():
            interviewer_lookup[row["Label"]] = row.to_dict()
    selected_interviewer_label = st.selectbox("Interviewer profile", list(interviewer_lookup.keys()))
    interviewer_profile = interviewer_lookup[selected_interviewer_label] or {}

    manual_name = ""
    manual_email = ""
    manual_role = ""
    manual_region = ""
    if interviewer_profile:
        st.markdown(
            f"""
            <div class="section-panel">
                <strong>{interviewer_profile.get("Full_Name", "")}</strong><br>
                <span style="color:#5e6775;font-size:13px">
                    {interviewer_profile.get("Role", "")} · {interviewer_profile.get("Email", "")} · {interviewer_profile.get("Region", "")}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            manual_name = st.text_input("Interviewer name *")
            manual_email = st.text_input("Interviewer email")
        with c2:
            manual_role = st.text_input("Interviewer role")
            manual_region = st.text_input("Interviewer region")

    st.markdown("### Candidate Profile")
    c1, c2, c3 = st.columns(3)
    with c1:
        first_name = st.text_input("First name *", value=prefill.get("Candidate_First_Name", ""))
        candidate_email = st.text_input("Candidate email", value=prefill.get("Candidate_Email", ""))
        position = st.selectbox("Position applying for", POSITIONS, index=POSITIONS.index(prefill.get("Position_Interest")) if prefill.get("Position_Interest") in POSITIONS else 0)
        site_assignment = st.text_input("Site / account", value=prefill.get("Preferred_Site", ""))
    with c2:
        last_name = st.text_input("Last name *", value=prefill.get("Candidate_Last_Name", ""))
        candidate_phone = st.text_input("Candidate phone", value=prefill.get("Candidate_Phone", ""))
        experience = st.selectbox("Security experience", EXPERIENCE_OPTIONS, index=EXPERIENCE_OPTIONS.index(prefill.get("Years_of_Experience")) if prefill.get("Years_of_Experience") in EXPERIENCE_OPTIONS else 0)
        candidate_city = st.text_input("City", value=prefill.get("Candidate_City", ""))
    with c3:
        interview_date = st.date_input("Interview date", value=date.today())
        interview_time = st.time_input("Interview time", value=datetime.now().time().replace(second=0, microsecond=0))
        candidate_state = st.text_input("State", value=prefill.get("Candidate_State", ""))
        follow_up_date = st.date_input("Follow-up date", value=date.today())

    st.markdown("### Candidate Readiness")
    prefill_shifts = [item.strip() for item in str(prefill.get("Available_Shifts", "")).split(",") if item.strip()]
    r1, r2, r3 = st.columns(3)
    with r1:
        shifts = st.multiselect("Available shifts", SHIFT_OPTIONS, default=[s for s in prefill_shifts if s in SHIFT_OPTIONS])
        transportation = st.radio("Reliable transportation", ["Yes", "No"], horizontal=True, index=0 if str(prefill.get("Reliable_Transportation", "Yes")) != "No" else 1)
    with r2:
        guard_card = st.radio("Guard card", ["Yes", "No", "In Progress"], horizontal=True, index=["Yes", "No", "In Progress"].index(prefill.get("Guard_Card_Status")) if prefill.get("Guard_Card_Status") in ["Yes", "No", "In Progress"] else 0)
        firearm_permit = st.radio("Firearm permit", ["Yes", "No", "N/A"], horizontal=True, index=["Yes", "No", "N/A"].index(prefill.get("Firearm_Permit_Status")) if prefill.get("Firearm_Permit_Status") in ["Yes", "No", "N/A"] else 2)
    with r3:
        cpr = st.radio("CPR certified", ["Yes", "No", "Expired"], horizontal=True, index=["Yes", "No", "Expired"].index(prefill.get("CPR_Certified")) if prefill.get("CPR_Certified") in ["Yes", "No", "Expired"] else 1)
        first_aid = st.radio("First aid certified", ["Yes", "No", "Expired"], horizontal=True, index=["Yes", "No", "Expired"].index(prefill.get("First_Aid_Certified")) if prefill.get("First_Aid_Certified") in ["Yes", "No", "Expired"] else 1)
        bg_check = st.radio("Background check", ["Pass", "Fail", "Pending"], horizontal=True, index=["Pass", "Fail", "Pending"].index(prefill.get("Can_Pass_Background_Check")) if prefill.get("Can_Pass_Background_Check") in ["Pass", "Fail", "Pending"] else 2)
        drug_test = st.radio("Drug test", ["Pass", "Fail", "Pending"], horizontal=True, index=["Pass", "Fail", "Pending"].index(prefill.get("Can_Pass_Drug_Test")) if prefill.get("Can_Pass_Drug_Test") in ["Pass", "Fail", "Pending"] else 2)

    st.markdown("### Scoring Rubric")
    s1, s2 = st.columns(2)
    with s1:
        professionalism = st.slider("Professionalism", 1, 10, 7)
        communication = st.slider("Communication", 1, 10, 7)
        punctuality = st.slider("Punctuality", 1, 10, 7)
        confidence = st.slider("Confidence", 1, 10, 7)
    with s2:
        appearance = st.slider("Appearance", 1, 10, 7)
        situational = st.slider("Situational awareness", 1, 10, 7)
        customer_service = st.slider("Customer service", 1, 10, 7)
        leadership = st.slider("Leadership potential", 1, 10, 7)
    behavior_score = professionalism + communication + punctuality + confidence + appearance + situational + customer_service + leadership
    st.info(f"Behavior score: {behavior_score} / 80")

    st.markdown("### Structured Questions")
    answers = {}
    question_scores = {}
    for question_id, question_text, category in INTERVIEW_QUESTIONS:
        st.markdown(
            f"""
            <div class="question-card">
                <div class="question-meta">{question_id} · {category}</div>
                <div><strong>{question_text}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        qa, qs = st.columns([4, 1])
        with qa:
            answers[question_id] = st.text_area(
                f"{question_id} answer",
                value=prefill_answers.get(question_id, ""),
                key=f"admin_answer_{question_id}",
                height=84,
                label_visibility="collapsed",
                placeholder="Capture the candidate's answer and examples.",
            )
        with qs:
            question_scores[question_id] = st.slider(f"{question_id} score", 1, 5, 3, key=f"admin_score_{question_id}")
    question_score = sum(question_scores.values())
    st.info(f"Question score: {question_score} / 125")

    st.markdown("### Scenario Exercise")
    scenario_name = st.selectbox("Scenario", list(INCIDENT_SCENARIOS.keys()))
    scenario = INCIDENT_SCENARIOS[scenario_name]
    st.markdown(
        f"""
        <div class="section-panel">
            <strong>Scenario Prompt</strong><br>
            <span style="color:#374151">{scenario['prompt']}</span><br><br>
            <strong>Ideal response points</strong><br>
            <span style="color:#5e6775;font-size:13px">{' | '.join(scenario['ideal_points'])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    scenario_response = st.text_area("Candidate scenario response", height=150)
    scenario_score = st.slider("Scenario score", 1, 10, 5)

    audio_payload = render_audio_capture()

    st.markdown("### Summary and Recommendation")
    n1, n2 = st.columns(2)
    with n1:
        strengths = st.text_area("Strengths", height=120)
        development = st.text_area("Areas for development", height=120)
    with n2:
        candidate_summary = st.text_area("Candidate summary", value=prefill.get("Candidate_Summary", ""), height=120)
        interviewer_notes = st.text_area("Interviewer notes", height=120)
        hr_notes = st.text_area("Internal HR notes", height=120)

    final_score = round((behavior_score / 80) * 45 + (question_score / 125) * 40 + (scenario_score / 10) * 15, 1)
    default_recommendation = score_to_recommendation(final_score)
    f1, f2, f3 = st.columns([1, 1, 1.3])
    with f1:
        recommendation = st.selectbox("Hiring recommendation", ["Strong Hire", "Hire", "Maybe", "Do Not Hire"], index=["Strong Hire", "Hire", "Maybe", "Do Not Hire"].index(default_recommendation))
    with f2:
        hiring_status = st.selectbox("Hiring status", ["Pending", "Approved", "Rejected", "On Hold"])
    with f3:
        st.markdown(
            f"""
            <div class="section-panel">
                <strong>Composite Score</strong><br>
                <span style="font-size:30px;font-family:'Space Grotesk',sans-serif;color:#aa7b26">{final_score} / 100</span><br>
                <span style="color:#5e6775;font-size:13px">Behavior 45% · Questions 40% · Scenario 15%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("Save interview", type="primary", use_container_width=True):
        interviewer_name = interviewer_profile.get("Full_Name", "").strip() if interviewer_profile else manual_name.strip()
        interviewer_email = interviewer_profile.get("Email", "").strip() if interviewer_profile else manual_email.strip()
        interviewer_role = interviewer_profile.get("Role", "").strip() if interviewer_profile else manual_role.strip()
        interviewer_region = interviewer_profile.get("Region", "").strip() if interviewer_profile else manual_region.strip()

        if not interviewer_name:
            st.error("Choose an interviewer profile or enter an interviewer name.")
        elif not first_name.strip() or not last_name.strip():
            st.error("Candidate first and last name are required.")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            interview_id = f"INT-{uuid.uuid4().hex[:8].upper()}"
            audio_meta = {
                "file_id": "",
                "file_name": "",
                "mime_type": "",
                "drive_link": "",
                "duration_seconds": "",
                "status": "Not Recorded",
            }

            upload_profile = interviewer_profile.copy() if interviewer_profile else {
                "Full_Name": interviewer_name,
                "Drive_Folder_ID": "",
                "Drive_Folder_Link": "",
            }
            if audio_payload:
                filename = f"{sanitize_name(first_name)}-{sanitize_name(last_name)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{audio_payload['name'].split('.')[-1] if '.' in audio_payload['name'] else 'wav'}"
                upload_result = upload_audio_to_drive(audio_payload["bytes"], audio_payload["mime_type"], filename, upload_profile)
                if upload_result.get("ok"):
                    audio_meta = {
                        "file_id": upload_result.get("file_id", ""),
                        "file_name": upload_result.get("file_name", filename),
                        "mime_type": upload_result.get("mime_type", audio_payload["mime_type"]),
                        "drive_link": upload_result.get("drive_link", ""),
                        "duration_seconds": audio_payload.get("duration_seconds", ""),
                        "status": "Uploaded to Drive",
                    }
                    if interviewer_profile and upload_result.get("folder_id") and not interviewer_profile.get("Drive_Folder_ID", ""):
                        interviewer_profile["Drive_Folder_ID"] = upload_result.get("folder_id", "")
                        interviewer_profile["Drive_Folder_Link"] = upload_result.get("folder_link", "")
                        interviewer_profile["Updated_At"] = now
                        upsert_interviewer(interviewer_profile)
                else:
                    audio_meta["status"] = f"Upload failed: {upload_result.get('message', 'Unknown error')}"

            payload = {
                "Interview_ID": interview_id,
                "Created_At": now,
                "Prefill_ID": prefill.get("Prefill_ID", ""),
                "Interview_Date": str(interview_date),
                "Interview_Time": str(interview_time),
                "Follow_Up_Date": str(follow_up_date),
                "Interviewer_ID": interviewer_profile.get("Interviewer_ID", ""),
                "Interviewer_Name": interviewer_name,
                "Interviewer_Email": interviewer_email,
                "Interviewer_Role": interviewer_role,
                "Interviewer_Region": interviewer_region,
                "Candidate_First_Name": first_name.strip(),
                "Candidate_Last_Name": last_name.strip(),
                "Candidate_Email": candidate_email.strip(),
                "Candidate_Phone": candidate_phone.strip(),
                "Candidate_City": candidate_city.strip(),
                "Candidate_State": candidate_state.strip(),
                "Position_Applying_For": position,
                "Site_Assignment": site_assignment.strip(),
                "Years_of_Experience": experience,
                "Available_Shifts": ", ".join(shifts),
                "Reliable_Transportation": transportation,
                "Guard_Card_Status": guard_card,
                "Firearm_Permit_Status": firearm_permit,
                "CPR_Certified": cpr,
                "First_Aid_Certified": first_aid,
                "Can_Pass_Background_Check": bg_check,
                "Can_Pass_Drug_Test": drug_test,
                "Behavior_Score": behavior_score,
                "Question_Score": question_score,
                "Scenario_Score": scenario_score,
                "Final_Interview_Score": final_score,
                "Hiring_Recommendation": recommendation,
                "Hiring_Status": hiring_status,
                "Scenario_Name": scenario_name,
                "Scenario_Response": scenario_response.strip(),
                "Strengths": strengths.strip(),
                "Areas_for_Development": development.strip(),
                "Candidate_Summary": candidate_summary.strip(),
                "Interviewer_Notes": interviewer_notes.strip(),
                "Internal_HR_Notes": hr_notes.strip(),
                "Prefill_Answers_JSON": json.dumps(prefill_answers),
                "Question_Answers_JSON": json.dumps(answers),
                "Question_Scores_JSON": json.dumps(question_scores),
                "Audio_File_ID": audio_meta["file_id"],
                "Audio_File_Name": audio_meta["file_name"],
                "Audio_Mime_Type": audio_meta["mime_type"],
                "Audio_Drive_Link": audio_meta["drive_link"],
                "Audio_Duration_Seconds": audio_meta["duration_seconds"],
                "Audio_Status": audio_meta["status"],
            }
            if append_record("Interviews", INTERVIEW_HEADERS, payload):
                st.success(f"Interview saved. ID: {interview_id}")
                if audio_meta["status"].startswith("Upload failed"):
                    st.warning(audio_meta["status"])
                st.balloons()
            else:
                st.error("Could not save the interview.")


def render_archive(interviews_df: pd.DataFrame) -> None:
    render_hero(
        "Interview Archive",
        "Filter saved interviews, review structured answers, and play back interview audio directly from Drive inside Streamlit.",
    )

    if interviews_df.empty:
        st.info("No interviews have been saved yet.")
        return

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search = st.text_input("Search candidate")
    with f2:
        interviewer_filter = st.selectbox("Interviewer", ["All"] + sorted([x for x in interviews_df["Interviewer_Name"].dropna().astype(str).unique().tolist() if x]))
    with f3:
        status_filter = st.selectbox("Hiring status", ["All"] + sorted([x for x in interviews_df["Hiring_Status"].dropna().astype(str).unique().tolist() if x]))
    with f4:
        audio_filter = st.selectbox("Audio", ["All", "With Audio", "Without Audio"])

    filtered = interviews_df.copy()
    if search.strip():
        filtered = filtered[filtered["Candidate_Name"].str.contains(search, case=False, na=False)]
    if interviewer_filter != "All":
        filtered = filtered[filtered["Interviewer_Name"] == interviewer_filter]
    if status_filter != "All":
        filtered = filtered[filtered["Hiring_Status"] == status_filter]
    if audio_filter == "With Audio":
        filtered = filtered[filtered["Has_Audio"]]
    elif audio_filter == "Without Audio":
        filtered = filtered[~filtered["Has_Audio"]]

    st.dataframe(
        filtered[
            [
                "Interview_ID",
                "Candidate_Name",
                "Position_Applying_For",
                "Interviewer_Name",
                "Final_Interview_Score",
                "Hiring_Recommendation",
                "Hiring_Status",
                "Audio_Status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=340,
    )

    selected_id = st.selectbox("Open interview", filtered["Interview_ID"].tolist())
    selected = filtered[filtered["Interview_ID"] == selected_id].iloc[0].to_dict()
    answers = safe_json_loads(selected.get("Question_Answers_JSON", "{}"))
    scores = safe_json_loads(selected.get("Question_Scores_JSON", "{}"))

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### Summary")
        st.markdown(
            f"""
            <div class="section-panel">
                <strong>{selected.get('Candidate_Name', '')}</strong><br>
                <span style="color:#5e6775;font-size:13px">
                    {selected.get('Position_Applying_For', '')} · {selected.get('Interviewer_Name', '')} · {selected.get('Hiring_Status', '')}
                </span><br><br>
                <strong>Composite score:</strong> {selected.get('Final_Interview_Score', '')}<br>
                <strong>Recommendation:</strong> {selected.get('Hiring_Recommendation', '')}<br>
                <strong>Scenario:</strong> {selected.get('Scenario_Name', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("Candidate summary:", selected.get("Candidate_Summary", "") or "Not captured")
        st.write("Strengths:", selected.get("Strengths", "") or "Not captured")
        st.write("Areas for development:", selected.get("Areas_for_Development", "") or "Not captured")
        st.write("Interviewer notes:", selected.get("Interviewer_Notes", "") or "Not captured")

        st.markdown("### Answers")
        for question_id, question_text, category in INTERVIEW_QUESTIONS:
            with st.expander(f"{question_id} · {category} · Score {scores.get(question_id, '')}", expanded=False):
                st.write(question_text)
                st.write(answers.get(question_id, "") or "No answer recorded.")

    with right:
        st.markdown("### Playback")
        audio_file_id = str(selected.get("Audio_File_ID", "")).strip()
        audio_mime = selected.get("Audio_Mime_Type", "") or "audio/wav"
        if audio_file_id:
            audio_bytes = download_drive_audio(audio_file_id)
            if audio_bytes:
                st.audio(audio_bytes, format=audio_mime)
                st.download_button(
                    "Download audio",
                    data=audio_bytes,
                    file_name=selected.get("Audio_File_Name", "interview-audio.wav"),
                    mime=audio_mime,
                    use_container_width=True,
                )
            else:
                st.warning("Audio metadata exists, but playback could not load from Drive.")
        else:
            st.info("No recording attached to this interview.")
        drive_link = selected.get("Audio_Drive_Link", "")
        if drive_link:
            st.link_button("Open file in Google Drive", drive_link, use_container_width=True)
        st.markdown("### Internal HR Notes")
        st.write(selected.get("Internal_HR_Notes", "") or "No internal HR notes.")


def render_question_bank() -> None:
    render_hero(
        "Question and Scenario Library",
        "Shared reference material for interviewers. The gold treatment is intentionally soft so the content feels premium without being loud.",
    )
    tab1, tab2 = st.tabs(["Questions", "Scenarios"])
    with tab1:
        grouped = {}
        for question_id, question_text, category in INTERVIEW_QUESTIONS:
            grouped.setdefault(category, []).append((question_id, question_text))
        for category, questions in grouped.items():
            st.subheader(category)
            for question_id, question_text in questions:
                st.markdown(
                    f"""
                    <div class="question-card">
                        <div class="question-meta">{question_id} · {category}</div>
                        <div><strong>{question_text}</strong></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    with tab2:
        for title, scenario in INCIDENT_SCENARIOS.items():
            with st.expander(title, expanded=False):
                st.write(scenario["prompt"])
                for point in scenario["ideal_points"]:
                    st.markdown(f"- {point}")


def render_analytics(interviews_df: pd.DataFrame, prefill_df: pd.DataFrame) -> None:
    render_hero(
        "Analytics",
        "Review pipeline volume, interviewer activity, scoring patterns, and audio coverage across the interview operation.",
    )
    if interviews_df.empty:
        st.info("No interview analytics yet.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Recommendations")
        st.bar_chart(interviews_df["Hiring_Recommendation"].value_counts())
        st.markdown("### Positions")
        st.bar_chart(interviews_df["Position_Applying_For"].value_counts())
    with c2:
        st.markdown("### Average Score by Interviewer")
        interviewer_scores = interviews_df.groupby("Interviewer_Name")["Final_Interview_Score"].mean().sort_values(ascending=False)
        st.bar_chart(interviewer_scores)
        st.markdown("### Audio Uploads by Interviewer")
        audio_by_interviewer = interviews_df.groupby("Interviewer_Name")["Has_Audio"].sum().sort_values(ascending=False)
        st.bar_chart(audio_by_interviewer)

    st.markdown("### Pipeline Snapshot")
    st.dataframe(
        pd.DataFrame(
            {
                "Metric": ["Prefill submissions", "Interviews completed", "Audio recordings"],
                "Value": [len(prefill_df), len(interviews_df), int(interviews_df["Has_Audio"].sum())],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_admin() -> None:
    render_hero(
        "Admin and Auto Setup",
        "This project now auto-creates the spreadsheet, the needed worksheets, the Drive audio root, and shares those assets to entremotivator@gmail.com automatically.",
    )

    conn = connection_summary()
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric("Sheets", "Ready" if conn["sheets"] else "Missing", "Spreadsheet is created or opened automatically")
    with c2:
        render_metric("Drive", "Ready" if conn["drive"] else "Missing", "Audio folders and files are created automatically")
    with c3:
        render_metric("Share Email", conn["share_email"], "New assets are granted access automatically")

    if st.button("Create or repair all backend assets", type="primary", use_container_width=True):
        sheet = get_spreadsheet()
        parent_folder_id = get_audio_parent_folder_id()
        interviewers_ws = ensure_worksheet("Interviewers", INTERVIEWER_HEADERS)
        prefill_ws = ensure_worksheet("Prefill_Responses", PREFILL_HEADERS)
        interviews_ws = ensure_worksheet("Interviews", INTERVIEW_HEADERS)
        if sheet and parent_folder_id and interviewers_ws and prefill_ws and interviews_ws:
            st.success("Spreadsheet, worksheets, and audio root folder are ready.")
        else:
            st.error("Some assets could not be prepared. Check credentials and API access.")

    st.markdown("### Current Links")
    if conn["spreadsheet_link"]:
        st.link_button("Open active Google Sheet", conn["spreadsheet_link"])
    else:
        st.info("The spreadsheet link will appear after the first successful creation/open.")

    st.markdown("### Secrets expected by this app")
    st.code(
        """gsheet_url = ""
gsheet_name = "Hud Security Interview Hub"
drive_parent_folder_id = ""
audio_root_folder_name = "Hud Security Interview Audio"
default_share_email = "entremotivator@gmail.com"
admin_username = "admin"
admin_password = "change-this-password"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..." """,
        language="toml",
    )

    st.markdown("### What now")
    st.markdown(
        """
        1. Run this admin app once.
        2. Open `Admin` and click `Create or repair all backend assets`.
        3. Share the standalone questionnaire link with candidates.
        4. Use the `Conduct Interview` page to import a prefill record and continue into the live interview.
        """
    )


apply_theme()
ensure_admin_auth()

with st.sidebar:
    st.markdown('<div class="sidebar-mark">Hud Security</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-submark">Admin Interview Suite</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigate",
        [
            "Dashboard",
            "Conduct Interview",
            "Interviewer Profiles",
            "Prefill Queue",
            "Interview Archive",
            "Question Bank",
            "Analytics",
            "Admin",
        ],
        label_visibility="collapsed",
    )

    conn = connection_summary()
    st.divider()
    st.caption("Connections")
    st.markdown(status_pill("Sheets Ready", "good") if conn["sheets"] else status_pill("Sheets Offline", "bad"), unsafe_allow_html=True)
    st.markdown(status_pill("Drive Ready", "good") if conn["drive"] else status_pill("Drive Offline", "warn"), unsafe_allow_html=True)
    st.markdown(status_pill("Mic Capture", "good") if conn["audio_input"] else status_pill("Upload Mode", "neutral"), unsafe_allow_html=True)
    if configured_admin_password():
        st.divider()
        st.caption("Security")
        st.markdown(status_pill("Admin Locked", "good"), unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True):
            st.session_state["hud_security_admin_authed"] = False
            st.rerun()


interviewers_df = load_interviewers_df()
prefill_df = load_prefill_df()
interviews_df = load_interviews_df()

if page == "Dashboard":
    render_dashboard(interviews_df, interviewers_df, prefill_df)
elif page == "Conduct Interview":
    render_new_interview(interviewers_df, prefill_df)
elif page == "Interviewer Profiles":
    render_interviewer_profiles(interviewers_df)
elif page == "Prefill Queue":
    render_prefill_queue(prefill_df)
elif page == "Interview Archive":
    render_archive(interviews_df)
elif page == "Question Bank":
    render_question_bank()
elif page == "Analytics":
    render_analytics(interviews_df, prefill_df)
else:
    render_admin()

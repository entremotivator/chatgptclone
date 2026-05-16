"""
Hud Security Candidate Prefill Questionnaire

Standalone Streamlit app that writes candidate pre-interview answers
into the same Google Sheet used by the admin interview app.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Hud Security Candidate Intake",
    page_icon="SG",
    layout="wide",
    initial_sidebar_state="collapsed",
)


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

PREFILL_QUESTIONS = [
    ("Q1", "Tell us about your security experience or similar work background."),
    ("Q2", "Why do you want to work in security right now?"),
    ("Q3", "What shifts and work environments are best for you?"),
    ("Q4", "Describe a time you had to stay calm during conflict."),
    ("Q5", "How do you handle difficult customers, residents, or visitors?"),
    ("Q6", "How would you respond if you found someone in a restricted area?"),
    ("Q7", "What would you include in an incident report?"),
    ("Q8", "How do you stay alert during long or overnight shifts?"),
    ("Q9", "What certifications or licenses do you already have?"),
    ("Q10", "How comfortable are you with CCTV, access control, radios, or patrol software?"),
    ("Q11", "Describe a time you had to follow detailed procedures exactly."),
    ("Q12", "What would you do during a fire alarm or medical emergency until backup arrives?"),
    ("Q13", "How do you handle working nights, weekends, holidays, or changing schedules?"),
    ("Q14", "What kind of site are you strongest on: residential, retail, office, patrol, event, or industrial?"),
    ("Q15", "Anything else the interviewer should know before meeting you?"),
]


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            --ink: #1b2430;
            --soft: #5e6775;
            --border: #e6ddd1;
            --gold: #aa7b26;
            --panel: rgba(255,255,255,0.88);
        }

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
            color: var(--gold) !important;
        }

        p, span, div, li, label, small, strong, td, th {
            color: var(--gold) !important;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stTextInputRootElement"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] *,
        [data-testid="stMultiSelect"] *,
        [data-testid="stRadio"] *,
        .stButton button {
            color: var(--gold) !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #b6944b !important;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top right, rgba(170, 123, 38, 0.10), transparent 22%),
                linear-gradient(180deg, #faf6ee 0%, #ffffff 100%);
        }

        h1, h2, h3 {
            font-family: 'Space Grotesk', sans-serif !important;
            color: var(--gold);
            font-weight: 800;
        }

        .hero {
            background: linear-gradient(135deg, #143247 0%, #1f465f 64%, #89621e 150%);
            color: white;
            border-radius: 26px;
            padding: 28px 30px;
            margin-bottom: 18px;
        }

        .eyebrow {
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.78);
            font-weight: 800;
            margin-bottom: 8px;
        }

        .title {
            font-size: 38px;
            font-weight: 800;
            line-height: 1.05;
        }

        .subtitle {
            font-size: 15px;
            line-height: 1.6;
            color: rgba(255,255,255,0.84);
            max-width: 820px;
        }

        .hero *, .hero div, .hero span {
            color: #fff !important;
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }

        .question-card {
            background: rgba(255,255,255,0.92);
            border: 1px solid var(--border);
            border-left: 4px solid var(--gold);
            border-radius: 14px;
            padding: 15px 16px 8px 16px;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def safe_secret(key: str, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def get_sheet_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def get_spreadsheet():
    client = get_sheet_client()
    if client is None:
        return None
    spreadsheet_url = str(safe_secret("gsheet_url", "")).strip() or load_local_config().get("gsheet_url", "")
    if not spreadsheet_url:
        return None
    try:
        return client.open_by_url(spreadsheet_url)
    except Exception:
        return None


def ensure_prefill_worksheet():
    spreadsheet = get_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        worksheet = spreadsheet.worksheet("Prefill_Responses")
    except Exception:
        worksheet = spreadsheet.add_worksheet(title="Prefill_Responses", rows=1000, cols=40)
        worksheet.update([PREFILL_HEADERS], "A1")
        return worksheet

    headers = worksheet.row_values(1)
    if not headers:
        worksheet.update([PREFILL_HEADERS], "A1")
        return worksheet
    merged = headers[:]
    for header in PREFILL_HEADERS:
        if header not in merged:
            merged.append(header)
    if merged != headers:
        worksheet.update([merged], "A1")
    return worksheet


def append_prefill(record: dict) -> bool:
    worksheet = ensure_prefill_worksheet()
    if worksheet is None:
        return False
    try:
        headers = worksheet.row_values(1)
        worksheet.append_row([str(record.get(header, "")) for header in headers], value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False


apply_theme()

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">Hud Security Candidate Intake</div>
        <div class="title">Pre-Interview Questionnaire</div>
        <div class="subtitle">
            Complete this longer intake before your interview so the Hud Security hiring team can review your background, availability, certifications, site preferences, and written answers in advance.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

sheet_ready = get_spreadsheet() is not None
if not sheet_ready:
    st.error("The shared interview sheet is not ready yet. Open the admin app first and finish the Admin setup page.")
else:
    st.markdown('<div class="panel"><strong>What happens next</strong><br>Your answers go to the shared Hud Security hiring sheet so the interviewer can prefill your interview record before the live interview starts. This helps the admin team review your experience, certifications, preferred shifts, and written answers ahead of time.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        first_name = st.text_input("First name *")
        candidate_email = st.text_input("Email *")
        position = st.selectbox("Position of interest", POSITIONS)
        preferred_site = st.text_input("Preferred site or area")
    with c2:
        last_name = st.text_input("Last name *")
        candidate_phone = st.text_input("Phone *")
        experience = st.selectbox("Years of experience", EXPERIENCE_OPTIONS)
        candidate_city = st.text_input("City")
    with c3:
        candidate_state = st.text_input("State")
        start_availability = st.date_input("Earliest start date", value=date.today())
        shifts = st.multiselect("Available shifts", SHIFT_OPTIONS)

    r1, r2, r3 = st.columns(3)
    with r1:
        transportation = st.radio("Reliable transportation", ["Yes", "No"], horizontal=True)
        guard_card = st.radio("Guard card", ["Yes", "No", "In Progress"], horizontal=True)
    with r2:
        firearm_permit = st.radio("Firearm permit", ["Yes", "No", "N/A"], horizontal=True)
        cpr = st.radio("CPR certified", ["Yes", "No", "Expired"], horizontal=True)
    with r3:
        first_aid = st.radio("First aid certified", ["Yes", "No", "Expired"], horizontal=True)
        bg_check = st.radio("Background check", ["Pass", "Fail", "Pending"], horizontal=True)
        drug_test = st.radio("Drug test", ["Pass", "Fail", "Pending"], horizontal=True)

    candidate_summary = st.text_area(
        "Short summary about yourself",
        height=120,
        placeholder="Share your background, strongest skills, and the kind of security work you are looking for.",
    )

    st.markdown("### Written Questions")
    answers = {}
    for question_id, question_text in PREFILL_QUESTIONS:
        st.markdown(
            f"""
            <div class="question-card">
                <strong>{question_id}</strong><br>
                <span>{question_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        answers[question_id] = st.text_area(
            f"{question_id} response",
            key=f"prefill_{question_id}",
            height=100,
            label_visibility="collapsed",
        )

    if st.button("Submit pre-interview questionnaire", type="primary", use_container_width=True):
        if not first_name.strip() or not last_name.strip() or not candidate_email.strip() or not candidate_phone.strip():
            st.error("First name, last name, email, and phone are required.")
        else:
            payload = {
                "Prefill_ID": f"PRE-{uuid.uuid4().hex[:8].upper()}",
                "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Submission_Status": "Submitted",
                "Candidate_First_Name": first_name.strip(),
                "Candidate_Last_Name": last_name.strip(),
                "Candidate_Email": candidate_email.strip(),
                "Candidate_Phone": candidate_phone.strip(),
                "Candidate_City": candidate_city.strip(),
                "Candidate_State": candidate_state.strip(),
                "Position_Interest": position,
                "Preferred_Site": preferred_site.strip(),
                "Years_of_Experience": experience,
                "Available_Shifts": ", ".join(shifts),
                "Reliable_Transportation": transportation,
                "Guard_Card_Status": guard_card,
                "Firearm_Permit_Status": firearm_permit,
                "CPR_Certified": cpr,
                "First_Aid_Certified": first_aid,
                "Can_Pass_Background_Check": bg_check,
                "Can_Pass_Drug_Test": drug_test,
                "Start_Availability": str(start_availability),
                "Candidate_Summary": candidate_summary.strip(),
                "Prefill_Answers_JSON": json.dumps(answers),
                "Source_App": "hud_security_candidate_prefill_streamlit",
            }
            if append_prefill(payload):
                st.success("Your questionnaire was submitted successfully.")
                st.balloons()
            else:
                st.error("Could not submit your questionnaire. Please try again after the admin app setup is complete.")

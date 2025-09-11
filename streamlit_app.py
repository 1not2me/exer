import streamlit as st
import pandas as pd
from datetime import datetime
import re
from pathlib import Path
import os, shutil, tempfile

st.set_page_config(page_title='📋 מיפוי מדריכים - תשפ"ו', layout='centered')

DATA_DIR = Path("data")
CSV_FILE = DATA_DIR / "mapping_data.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "תאריך","שם משפחה","שם פרטי","מוסד/שירות ההכשרה","תחום התמחות",
    "רחוב","עיר","מיקוד","מספר סטודנטים","המשך הדרכה","טלפון","אימייל"
]

def atomic_write_csv(df: pd.DataFrame, path: Path):
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)
    df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
    shutil.move(tmp_path, path)

def save_persistent(new_rows: pd.DataFrame):
    if CSV_FILE.exists():
        existing = pd.read_csv(CSV_FILE)
    else:
        existing = pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in existing.columns: existing[c] = ""
        if c not in new_rows.columns: new_rows[c] = ""
    combined = pd.concat([existing[COLUMNS], new_rows[COLUMNS]], ignore_index=True)
    atomic_write_csv(combined, CSV_FILE)

# ===== טופס =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו")
with st.form("mapping_form"):
    last_name = st.text_input("שם משפחה *")
    first_name = st.text_input("שם פרטי *")
    institution = st.text_input("מוסד / שירות ההכשרה *")
    specialization = st.selectbox("תחום ההתמחות *", ["בחר מהרשימה","חינוך","בריאות","רווחה","אחר"])
    specialization_other = ""
    if specialization == "אחר":
        specialization_other = st.text_input("אם ציינת אחר, אנא כתוב את תחום ההתמחות *")
    street = st.text_input("רחוב *")
    city = st.text_input("עיר *")
    postal_code = st.text_input("מיקוד *")
    num_students = st.number_input("מספר סטודנטים שניתן לקלוט השנה *", min_value=0, step=1)
    continue_mentoring = st.radio("האם מעוניין/ת להמשיך להדריך השנה *", ["כן","לא"], horizontal=True)
    phone = st.text_input("טלפון * (לדוגמה: 050-1234567)")
    email = st.text_input("כתובת אימייל *")
    submit_btn = st.form_submit_button("שלח/י")

if submit_btn:
    errors = []
    if not last_name.strip(): errors.append("יש למלא שם משפחה")
    if not first_name.strip(): errors.append("יש למלא שם פרטי")
    if not institution.strip(): errors.append("יש למלא מוסד/שירות ההכשרה")
    if specialization == "בחר מהרשימה": errors.append("יש לבחור תחום התמחות")
    if specialization == "אחר" and not specialization_other.strip(): errors.append("יש למלא את תחום ההתמחות")
    if not street.strip(): errors.append("יש למלא רחוב")
    if not city.strip(): errors.append("יש למלא עיר")
    if not postal_code.strip(): errors.append("יש למלא מיקוד")
    if num_students <= 0: errors.append("יש להזין מספר סטודנטים גדול מ-0")
    if not re.match(r"^0\d{1,2}-\d{6,7}$", phone.strip()): errors.append("מספר הטלפון אינו תקין")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()): errors.append("כתובת האימייל אינה תקינה")

    if errors:
        for e in errors:
            st.error(e)
    else:
        data = {
            "תאריך": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "שם משפחה": [last_name],
            "שם פרטי": [first_name],
            "מוסד/שירות ההכשרה": [institution],
            "תחום התמחות": [specialization_other if specialization=="אחר" else specialization],
            "רחוב": [street],
            "עיר": [city],
            "מיקוד": [postal_code],
            "מספר סטודנטים": [int(num_students)],
            "המשך הדרכה": [continue_mentoring],
            "טלפון": [phone],
            "אימייל": [email]
        }
        save_persistent(pd.DataFrame(data))
        st.success("✅ הנתונים נשמרו בהצלחה!")

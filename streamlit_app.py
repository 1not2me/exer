# streamlit_app.py
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from io import BytesIO
from datetime import datetime
import re

import streamlit as st
import pandas as pd

# ===== הגדרות קבועות =====
st.set_page_config(page_title="מיפוי מדריכים לשיבוץ סטודנטים - תשפ\"ו", layout="centered")
ADMIN_PASSWORD = "rawan_0304"

# ספריית נתונים + קבצים
DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE = DATA_DIR / "mapping_data.csv"          # קובץ ראשי (Append-Only)
CSV_LOG_FILE = DATA_DIR / "mapping_data_log.csv"  # קובץ יומן הוספות (Append-Only)
SITES_FILE = DATA_DIR / "sites_catalog.csv"       # אופציונלי: קטלוג מוסדות/תחומים

# ===== רשימת תחומי התמחות =====
SPECIALIZATIONS = [
    "מערכות מידע רפואיות", "בריאות דיגיטלית", "רווחה", "חינוך", "קהילה",
    "סיעוד", "פסיכולוגיה קהילתית", "מנהל מערכות מידע", "ניתוח נתונים", "סיוע טכנולוגי",
    "אחר"
]

# ===== סדר עמודות =====
COLUMNS_ORDER = [
    "תאריך", "שם פרטי", "שם משפחה", "סטטוס מדריך", "מוסד", "תחום התמחות",
    "רחוב", "עיר", "מיקוד", "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך", "בקשות מיוחדות", "טלפון", "אימייל"
]

def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    known = [c for c in COLUMNS_ORDER if c in df.columns]
    extra = [c for c in df.columns if c not in known]
    return df[known + extra]

# ===== עיצוב =====
st.markdown("""
<style>
:root{
  --ink:#0f172a; 
  --muted:#475569; 
  --ring:rgba(99,102,241,.25); 
  --card:rgba(255,255,255,.85);
}
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top:1.1rem; }
[data-testid="stForm"]{
  background:var(--card);
  border:1px solid #e2e8f0;
  border-radius:16px;
  padding:18px 20px;
  box-shadow:0 8px 24px rgba(2,6,23,.06);
}
[data-testid="stWidgetLabel"] p{ text-align:right; margin-bottom:.25rem; color:var(--muted); }
[data-testid="stWidgetLabel"] p::after{ content: " :"; }
input, textarea, select{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

# ===== פונקציות עזר לקבצים =====
def load_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()

def save_master_row(row: dict) -> None:
    """שמירה מצטברת (Append-Only) של שורה חדשה ל־CSV הראשי + גיבוי מתוארך."""
    row_df = reorder_columns(pd.DataFrame([row]))
    file_exists = CSV_FILE.exists()
    # כתיבה מצטברת
    row_df.to_csv(
        CSV_FILE,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8-sig"
    )
    # גיבוי מלא
    try:
        df_all = load_csv_safely(CSV_FILE)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"mapping_data_{ts}.csv"
        reorder_columns(df_all).to_csv(backup_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print("⚠ שגיאה בגיבוי:", e)

def append_to_log(row_df: pd.DataFrame) -> None:
    row_df = reorder_columns(row_df.copy())
    file_exists = CSV_LOG_FILE.exists()
    row_df.to_csv(
        CSV_LOG_FILE,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8-sig"
    )

def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    df = reorder_columns(df.copy())
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            width = min(60, max(12, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
            ws.set_column(i, i, width)
    bio.seek(0)
    return bio.read()

# ===== מצב מנהל =====
params = st.query_params if hasattr(st, "query_params") else {}
is_admin_mode = (params.get("admin", "0") == "1")

if is_admin_mode:
    st.title("🔑 גישת מנהל - צפייה וייצוא נתונים")
    password = st.text_input("הכנס סיסמת מנהל", type="password")
    if password == ADMIN_PASSWORD:
        st.success("התחברת בהצלחה ✅")

        df_master = load_csv_safely(CSV_FILE)
        df_log = load_csv_safely(CSV_LOG_FILE)

        st.subheader("📦 קובץ ראשי (Append-Only)")
        st.write(f"סה\"כ רשומות: **{len(df_master)}**")
        if not df_master.empty:
            st.dataframe(reorder_columns(df_master), use_container_width=True)
            st.download_button(
                "📊 הורד Excel (ראשי)",
                data=dataframe_to_excel_bytes(df_master, "Master"),
                file_name="mapping_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.subheader("🧾 קובץ יומן (Append-Only)")
        st.write(f"סה\"כ רשומות ביומן: **{len(df_log)}**")
        if not df_log.empty:
            st.dataframe(reorder_columns(df_log), use_container_width=True)
            st.download_button(
                "📊 הורד Excel (יומן)",
                data=dataframe_to_excel_bytes(df_log, "Log"),
                file_name="mapping_data_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        if password:
            st.error("סיסמה שגויה")
    st.stop()

# ===== טופס למילוי =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - תשפ\"ו")
with st.form("mapping_form"):
    st.subheader("פרטים אישיים")
    first_name = st.text_input("שם פרטי *")
    last_name  = st.text_input("שם משפחה *")

    mentor_status = st.selectbox("סטטוס מדריך *", ["מדריך חדש (נדרש קורס)", "מדריך ממשיך"])

    st.subheader("מוסד")
    specialization = st.selectbox("תחום התמחות *", ["בחר מהרשימה"] + SPECIALIZATIONS)
    institute = st.text_input("מוסד *")

    st.subheader("כתובת המוסד")
    street = st.text_input("רחוב *")
    city = st.text_input("עיר *")
    postal_code = st.text_input("מיקוד *")

    num_students = st.selectbox("מספר סטודנטים שניתן לקלוט (1 או 2) *", [1, 2])
    continue_mentoring = st.radio("מעוניין להמשיך *", ["כן", "לא"])
    special_requests = st.text_area("בקשות מיוחדות")

    phone = st.text_input("טלפון * (0501234567)")
    email = st.text_input("אימייל *")

    submit_btn = st.form_submit_button("שלח/י")

if submit_btn:
    errors = []
    if not first_name.strip(): errors.append("שם פרטי חובה")
    if not last_name.strip(): errors.append("שם משפחה חובה")
    if specialization == "בחר מהרשימה": errors.append("יש לבחור תחום התמחות")
    if not institute.strip(): errors.append("יש למלא מוסד")
    if not street.strip(): errors.append("יש למלא רחוב")
    if not city.strip(): errors.append("יש למלא עיר")
    if not postal_code.strip(): errors.append("יש למלא מיקוד")
    if not re.match(r"^0?5\d{8}$", phone.strip().replace("-", "").replace(" ", "")):
        errors.append("טלפון לא תקין")
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()):
        errors.append("אימייל לא תקין")

    if errors:
        for e in errors: st.error(e)
    else:
        record = {
            "תאריך": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": first_name.strip(),
            "שם משפחה": last_name.strip(),
            "סטטוס מדריך": mentor_status,
            "מוסד": institute.strip(),
            "תחום התמחות": specialization,
            "רחוב": street.strip(),
            "עיר": city.strip(),
            "מיקוד": postal_code.strip(),
            "מספר סטודנטים שניתן לקלוט (1 או 2)": int(num_students),
            "מעוניין להמשיך": continue_mentoring,
            "בקשות מיוחדות": special_requests.strip(),
            "טלפון": phone.strip(),
            "אימייל": email.strip()
        }
        try:
            save_master_row(record)
            append_to_log(pd.DataFrame([record]))
            st.success("✅ הנתונים נשמרו בהצלחה! תודה רבה 🙏")
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")

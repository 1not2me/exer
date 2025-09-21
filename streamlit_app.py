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

DATA_DIR   = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE      = DATA_DIR / "שאלון_שיבוץ.csv"         # קובץ ראשי (מצטבר, לעולם לא מתאפס)
CSV_LOG_FILE  = DATA_DIR / "שאלון_שיבוץ_log.csv"     # יומן הוספות (Append-Only)
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")  # מומלץ לשים ב-secrets

# ספריית נתונים + קבצים
DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE = DATA_DIR / "mapping_data.csv"          # קובץ ראשי (נשמר ומעודכן)
CSV_LOG_FILE = DATA_DIR / "mapping_data_log.csv"  # קובץ יומן הוספות (Append-Only)
SITES_FILE = DATA_DIR / "sites_catalog.csv"       # אופציונלי: קטלוג מוסדות/תחומים

# ===== רשימת תחומי התמחות (ניתן לעדכן בהתאם לשאלון הסטודנטים) =====
SPECIALIZATIONS = [
    "מערכות מידע רפואיות", "בריאות דיגיטלית", "רווחה", "חינוך", "קהילה",
    "סיעוד", "פסיכולוגיה קהילתית", "מנהל מערכות מידע", "ניתוח נתונים", "סיוע טכנולוגי",
    "אחר"
]

# ===== סדר עמודות רצוי (כולל תאריך) =====
COLUMNS_ORDER = [
    "תאריך",
    "שם פרטי",
    "שם משפחה",
    "סטטוס מדריך",
    "מוסד",
    "תחום התמחות",
    "רחוב",
    "עיר",
    "מיקוד",
    "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך",
    "בקשות מיוחדות",
    "טלפון",
    "אימייל",
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
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception:
            try:
                return pd.read_csv(path, encoding="utf-8-sig")
            except Exception:
                return pd.DataFrame()
    return pd.DataFrame()

def save_master_dataframe(df: pd.DataFrame) -> None:
    df = reorder_columns(df.copy())
    temp_path = CSV_FILE.with_suffix(".tmp.csv")
    df.to_csv(temp_path, index=False, encoding="utf-8-sig")
    temp_path.replace(CSV_FILE)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"mapping_data_{ts}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")

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

# ===== קריאת קטלוג מוסדות/תחומים (אופציונלי) =====
def load_sites_catalog() -> pd.DataFrame:
    if not SITES_FILE.exists():
        return pd.DataFrame()
    df = load_csv_safely(SITES_FILE)
    if df.empty:
        st.warning("⚠ קובץ הקטלוג קיים אך ריק.")
        return pd.DataFrame()

    cols = {c.strip(): c for c in df.columns}
    def pick(*options):
        for opt in options:
            if opt in cols:
                return cols[opt]
        return None

    col_institute = pick('מוסד', 'שם מוסד', 'שם מוסד/שירות ההכשרה', 'Institution')
    col_spec      = pick('תחום התמחות', 'תחום', 'התמחות', 'Specialization')

    if not col_institute or not col_spec:
        st.warning("⚠ בקטלוג חסרות עמודות חובה: 'מוסד' ו'תחום התמחות'. הטופס יעבוד במצב קלט חופשי.")
        return pd.DataFrame()

    clean = (
        df[[col_institute, col_spec]]
        .rename(columns={col_institute: 'מוסד', col_spec: 'תחום התמחות'})
        .dropna().drop_duplicates().reset_index(drop=True)
    )
    for c in ['מוסד', 'תחום התמחות']:
        clean[c] = clean[c].astype(str).str.strip()
    return clean

sites_df = load_sites_catalog()
sites_available = not sites_df.empty
known_specs = sorted(sites_df['תחום התמחות'].dropna().unique().tolist()) if sites_available else SPECIALIZATIONS[:]
known_institutions = sorted(sites_df['מוסד'].dropna().unique().tolist()) if sites_available else []

# ===== בדיקת מצב מנהל =====
try:
    params = st.experimental_get_query_params()
    admin_flag = params.get("admin", ["0"])[0]
except Exception:
    admin_flag = "0"
is_admin_mode = (admin_flag == "1")

# ===== מצב מנהל =====
if is_admin_mode:
    st.title("🔑 גישת מנהל - צפייה וייצוא נתונים")

    password = st.text_input("הכנס סיסמת מנהל", type="password", key="admin_pwd_input")
    if password == ADMIN_PASSWORD:
        st.success("התחברת בהצלחה ✅")

        df_master = load_csv_safely(CSV_FILE)
        df_log = load_csv_safely(CSV_LOG_FILE)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📦 קובץ ראשי (מצטבר)")
            st.write(f"סה\"כ רשומות: **{len(df_master)}**")
        with col2:
            st.subheader("🧾 קובץ יומן (Append-Only)")
            st.write(f"סה\"כ רשומות (יומן): **{len(df_log)}**")

        st.markdown("### הצגת הקובץ הראשי")
        if not df_master.empty:
            st.dataframe(reorder_columns(df_master), use_container_width=True)
            st.download_button(
                "📊 הורד Excel (ראשי)",
                data=dataframe_to_excel_bytes(df_master, sheet_name="Master"),
                file_name="mapping_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_master_xlsx"
            )
        else:
            st.info("⚠ עדיין אין נתונים בקובץ הראשי.")

        st.markdown("---")
        st.markdown("### הצגת קובץ היומן (Append-Only)")
        if not df_log.empty:
            st.dataframe(reorder_columns(df_log), use_container_width=True)
            st.download_button(
                "📊 הורד Excel (יומן)",
                data=dataframe_to_excel_bytes(df_log, sheet_name="Log"),
                file_name="mapping_data_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_log_xlsx"
            )
        else:
            st.info("⚠ עדיין אין נתונים ביומן.")
    else:
        if password:
            st.error("סיסמה שגויה")
    st.stop()

# ===== טופס למילוי =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו")
st.write("""
שלום רב, מטרת טופס זה היא לאסוף מידע עדכני על מדריכים ומוסדות לקראת שיבוץ הסטודנטים לשנה הקרובה.  
אנא מלא/י את כל השדות בצורה מדויקת. המידע ישמש לצורך תכנון השיבוץ בלבד.
""")

with st.form("mapping_form"):
    st.subheader("פרטים אישיים")
    first_name = st.text_input("שם פרטי *", key="first_name")
    last_name  = st.text_input("שם משפחה *", key="last_name")

    mentor_status = st.selectbox(
        "סטטוס מדריך *",
        ["מדריך חדש (נדרש קורס)", "מדריך ממשיך"],
        help="מדריך חדש יישלח לקורס הכשרה מתאים.",
        key="mentor_status"
    )

    st.subheader("מוסד")
    spec_choice = st.selectbox("תחום התמחות *", ["בחר מהרשימה"] + known_specs, key="specialization")

    if sites_available and spec_choice in known_specs and spec_choice != "בחר מהרשימה":
        filtered_institutions = sorted(
            sites_df[sites_df['תחום התמחות'] == spec_choice]['מוסד'].dropna().unique().tolist()
        )
        institute_select = st.selectbox("מוסד *", ["בחר מהרשימה"] + filtered_institutions, key="institute_select")
    elif sites_available:
        institute_select = st.selectbox("מוסד *", ["בחר מהרשימה"] + known_institutions, key="institute_select")
    else:
        institute_select = st.text_input("מוסד *", key="institute_input")

    st.subheader("כתובת המוסד")
    street = st.text_input("רחוב *", key="street")
    city = st.text_input("עיר *", key="city")
    postal_code = st.text_input("מיקוד *", key="postal_code")

    st.subheader("קליטת סטודנטים")
    num_students = st.selectbox(
        "מספר סטודנטים שניתן לקלוט (1 או 2) *",
        [1, 2],
        help="על פי הנהלים – מדריך יכול להדריך עד שני סטודנטים לכל היותר.",
        key="num_students"
    )

    st.subheader("זמינות להמשך הדרכה")
    continue_mentoring = st.radio("מעוניין להמשיך *", ["כן", "לא"], key="continue_mentoring")

    st.subheader("בקשות מיוחדות")
    special_requests = st.text_area(
        "בקשות מיוחדות (למשל: הדרכה בערב, שפות, נגישות, אילוצים)",
        placeholder="כתבו כאן כל בקשה שתרצו שניקח בחשבון בשיבוץ",
        key="special_requests"
    )

    st.subheader("פרטי התקשרות")
    phone = st.text_input("טלפון * (אפשר גם בלי מקף)", key="phone")
    email = st.text_input("אימייל *", key="email")

    submit_btn = st.form_submit_button("שלח/י", use_container_width=True)

# ===== טיפול בטופס =====
if submit_btn:
    errors = []
    if not first_name.strip():
        errors.append("יש למלא 'שם פרטי'")
    if not last_name.strip():
        errors.append("יש למלא 'שם משפחה'")
    if spec_choice == "בחר מהרשימה":
        errors.append("יש לבחור 'תחום התמחות'")

    if sites_available:
        if institute_select == "בחר מהרשימה":
            errors.append("יש לבחור 'מוסד'")
        if (spec_choice in known_specs) and (institute_select in known_institutions):
            ok = not sites_df[(sites_df['תחום התמחות'] == spec_choice) &
                              (sites_df['מוסד'] == institute_select)].empty
            if not ok:
                errors.append("המוסד שנבחר אינו תואם ל'תחום התמחות' שבחרת.")
        final_institute = institute_select if institute_select != "בחר מהרשימה" else ""
    else:
        if not institute_select.strip():
            errors.append("יש למלא 'מוסד'")
        final_institute = institute_select.strip()

    if not street.strip():
        errors.append("יש למלא 'רחוב'")
    if not city.strip():
        errors.append("יש למלא 'עיר'")
    if not postal_code.strip():
        errors.append("יש למלא 'מיקוד'")

    phone_clean = phone.strip().replace("-", "").replace(" ", "")
    if not re.match(r"^(0?5\d{8})$", phone_clean):
        errors.append("מספר הטלפון אינו תקין (דוגמה: 0501234567)")

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()):
        errors.append("כתובת האימייל אינה תקינה")

    if errors:
        for e in errors:
            st.error(e)
    else:
        record = {
            "תאריך": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": first_name.strip(),
            "שם משפחה": last_name.strip(),
            "סטטוס מדריך": mentor_status,
            "מוסד": final_institute,
            "תחום התמחות": spec_choice,
            "רחוב": street.strip(),
            "עיר": city.strip(),
            "מיקוד": postal_code.strip(),
            "מספר סטודנטים שניתן לקלוט (1 או 2)": int(num_students),
            "מעוניין להמשיך": continue_mentoring,
            "בקשות מיוחדות": special_requests.strip(),
            "טלפון": phone_clean,
            "אימייל": email.strip()
        }
        new_row_df = pd.DataFrame([record])
        master_df = load_csv_safely(CSV_FILE)
        master_df = pd.concat([master_df, new_row_df], ignore_index=True)
        save_master_dataframe(master_df)
        append_to_log(new_row_df)

        st.success("✅ הנתונים נשמרו בהצלחה! תודה רבה 🙏")
        st.info("טיפ: ניתן לצפות/להוריד את הקבצים במצב מנהל ?admin=1 (עם הסיסמה).")

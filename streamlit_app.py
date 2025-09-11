import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import os, re, shutil, tempfile
from pathlib import Path

# ===== הגדרות =====
st.set_page_config(page_title='מיפוי מדריכים לשיבוץ סטודנטים - תשפ"ו', layout='centered')
ADMIN_PASSWORD = "rawan_0304"

# נתיבי שמירה מתמשכים (תיקיית data + גיבויים)
DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
CSV_FILE = DATA_DIR / "mapping_data.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# סדר עמודות קבוע
COLUMNS = [
    "תאריך","שם משפחה","שם פרטי","מוסד/שירות ההכשרה","תחום התמחות",
    "רחוב","עיר","מיקוד","מספר סטודנטים","המשך הדרכה","טלפון","אימייל"
]

# ===== עיצוב =====
st.markdown("""
<style>
:root{ --ink:#0f172a; --muted:#475569; --ring:rgba(99,102,241,.25); --card:rgba(255,255,255,.85); }
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
  background:var(--card); border:1px solid #e2e8f0; border-radius:16px; padding:18px 20px;
  box-shadow:0 8px 24px rgba(2,6,23,.06);
}
[data-testid="stWidgetLabel"] p{ text-align:right; margin-bottom:.25rem; color:var(--muted); }
[data-testid="stWidgetLabel"] p::after{ content:" :"; }
input, textarea, select{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

# ===== עזר: כתיבה אטומית + גיבוי =====
def atomic_write_csv(df: pd.DataFrame, path: Path):
    """כתיבה אטומית ל-CSV (מונעת קבצים פגומים), UTF-8-SIG לטובת אקסל."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)
    df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
    shutil.move(tmp_path, path)

def save_persistent(new_rows: pd.DataFrame):
    """מוסיף שורות חדשות, משמר היסטוריה, יוצר גיבוי XLSX עם RTL בכל שליחה."""
    # טען קיים או התחל חדש
    if CSV_FILE.exists():
        existing = pd.read_csv(CSV_FILE)
    else:
        existing = pd.DataFrame(columns=COLUMNS)

    # וידוא כל העמודות קיימות וסדר קבוע
    for c in COLUMNS:
        if c not in existing.columns: existing[c] = ""
        if c not in new_rows.columns: new_rows[c] = ""
    existing = existing[COLUMNS]
    new_rows = new_rows[COLUMNS]

    combined = pd.concat([existing, new_rows], ignore_index=True)

    # כתיבה אטומית ל-CSV המצטבר
    atomic_write_csv(combined, CSV_FILE)

    # גיבוי XLSX עם RTL + חותמת זמן
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_xlsx = BACKUP_DIR / f"mapping_backup_{timestamp}.xlsx"
    to_excel_rtl(combined, backup_xlsx)

    return combined

def to_excel_rtl(df: pd.DataFrame, file_path: Path) -> bytes:
    """יוצר קובץ XLSX עם דף מימין-לשמאל, מקפיא שורת כותרות ומגדיר רוחבי עמודות."""
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="מיפוי")
        ws = writer.book["מיפוי"]
        # RTL
        ws.sheet_view.rightToLeft = True
        # הקפאת שורת כותרות
        ws.freeze_panes = "A2"
        # רוחבי עמודות עדינים
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(12, max_len + 2), 40)
    # נחזיר גם bytes להורדה מיידית אם נרצה
    return file_path.read_bytes()

def make_excel_bytes(df: pd.DataFrame) -> bytes:
    """החזרת XLSX ב-bytes עם RTL בלי לכתוב לקובץ קבוע (בשביל הורדה)."""
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="מיפוי")
        ws = writer.book["מיפוי"]
        ws.sheet_view.rightToLeft = True
        ws.freeze_panes = "A2"
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(12, max_len + 2), 40)
    bio.seek(0)
    return bio.getvalue()

# בדיקה אם המשתמש במצב מנהל
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# ===== מצב מנהל =====
if is_admin_mode:
    st.title("🔑 גישת מנהל - צפייה וייצוא נתונים")
    password = st.text_input("הכנס סיסמת מנהל", type="password")

    if password == ADMIN_PASSWORD:
        try:
            df = pd.read_csv(CSV_FILE)
            # ודא סדר קבוע
            for c in COLUMNS:
                if c not in df.columns: df[c] = ""
            df = df[COLUMNS]

            st.success("התחברת בהצלחה ✅")
            st.dataframe(df, use_container_width=True)

            # כפתורי הורדה בצד ימין
            col1, col2, col3 = st.columns([1,1,5], gap="small")
            with col1:
                st.download_button(
                    "📥 הורד XLSX (מימין לשמאל)",
                    data=make_excel_bytes(df),
                    file_name="mapping_data_rtl.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col2:
                st.download_button(
                    "⬇️ הורד CSV",
                    data=df.to_csv(index=False).encode('utf-8-sig'),
                    file_name="mapping_data.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.caption("כמו כן, כל שליחה שומרת **גיבוי אוטומטי** בתיקיית data/backups.")

        except FileNotFoundError:
            st.warning("⚠ עדיין אין נתונים שנשמרו.")
    else:
        if password:
            st.error("סיסמה שגויה")
    st.stop()

# ===== טופס למילוי =====
st.title('📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ"ו')
st.write("""
שלום רב, מטרת טופס זה היא לאסוף מידע עדכני על מדריכים ומוסדות הכשרה לקראת שיבוץ הסטודנטים לשנת ההכשרה הקרובה.  
אנא מלא/י את כל השדות בצורה מדויקת. המידע ישמש לצורך תכנון השיבוץ בלבד.
""")

with st.form("mapping_form"):
    st.subheader("פרטים אישיים")
    last_name = st.text_input("שם משפחה *")
    first_name = st.text_input("שם פרטי *")

    st.subheader("מוסד והכשרה")
    institution = st.text_input("מוסד / שירות ההכשרה *")
    specialization = st.selectbox("תחום ההתמחות *", ["בחר מהרשימה", "חינוך", "בריאות", "רווחה", "אחר"])
    specialization_other = ""
    if specialization == "אחר":
        specialization_other = st.text_input("אם ציינת אחר, אנא כתוב את תחום ההתמחות *")

    st.subheader("כתובת מקום ההכשרה")
    street = st.text_input("רחוב *")
    city = st.text_input("עיר *")
    postal_code = st.text_input("מיקוד *")

    st.subheader("קליטת סטודנטים")
    num_students = st.number_input("מספר סטודנטים שניתן לקלוט השנה *", min_value=0, step=1)
    continue_mentoring = st.radio("האם מעוניין/ת להמשיך להדריך השנה *", ["כן", "לא"], horizontal=True)

    st.subheader("פרטי התקשרות")
    phone = st.text_input("טלפון * (לדוגמה: 050-1234567)")
    email = st.text_input("כתובת אימייל *")

    submit_btn = st.form_submit_button("שלח/י")

# ===== טיפול בטופס =====
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
            "תחום התמחות": [specialization_other if specialization == "אחר" else specialization],
            "רחוב": [street],
            "עיר": [city],
            "מיקוד": [postal_code],
            "מספר סטודנטים": [int(num_students)],
            "המשך הדרכה": [continue_mentoring],
            "טלפון": [phone],
            "אימייל": [email]
        }
        new_df = pd.DataFrame(data)
        save_persistent(new_df)  # מוסיף, לא מוחק, יוצר גיבוי

        st.success("✅ הנתונים נשמרו בהצלחה! ניתן להמשיך למלא טפסים נוספים.")

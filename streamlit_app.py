# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from io import BytesIO
import re

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="שאלון שיבוץ סטודנטים – תשפ״ו", layout="centered")

# ====== עיצוב מודרני + RTL ======
st.markdown("""
<style>
@font-face {
  font-family:'David';
  src:url('https://example.com/David.ttf') format('truetype');
}
html, body, [class*="css"] {
  font-family:'David',sans-serif!important;
}
:root{
  --bg-1:#e0f7fa;
  --bg-2:#ede7f6;
  --bg-3:#fff3e0;
  --bg-4:#fce4ec;
  --bg-5:#e8f5e9;
  --ink:#0f172a;
  --primary:#9b5de5;
  --primary-700:#f15bb5;
  --ring:rgba(155,93,229,.35);
}
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, var(--bg-2) 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, var(--bg-3) 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, var(--bg-4) 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, var(--bg-5) 0%, transparent 70%),
    linear-gradient(135deg, var(--bg-1) 0%, #ffffff 100%) !important;
  color: var(--ink);
}
.main .block-container{
  background: rgba(255,255,255,.78);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px;
  padding:2.5rem;
  margin-top:1rem;
}
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center;
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:18px!important;
  padding:1rem 2rem!important;
  font-size:1.1rem!important;
  font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important;
}
.stApp,.main,[data-testid="stSidebar"]{
  direction:rtl;
  text-align:right;
}
label,.stMarkdown,.stText,.stCaption{
  text-align:right!important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# קבצים/סודות
# =========================
CSV_FILE = Path("שאלון_שיבוץ.csv")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")

# מצב מנהל
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# =========================
# פונקציות עזר
# =========================
def load_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()

def append_row(row: dict, path: Path):
    df_new = pd.DataFrame([row])
    df_new.to_csv(path, mode="a", index=False, encoding="utf-8-sig", header=not path.exists())

def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "תשובות") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name=sheet, index=False)
        ws = w.sheets[sheet]
        for i, col in enumerate(df.columns):
            width = min(60, max(12, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
            ws.set_column(i, i, width)
    buf.seek(0)
    return buf.read()

def valid_email(v: str) -> bool:  return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))
def valid_phone(v: str) -> bool:  return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))
def valid_id(v: str) -> bool:     return bool(re.match(r"^\d{8,9}$", v.strip()))

# =========================
# עמוד מנהל
# =========================
if is_admin_mode:
    st.title("🔑 גישת מנהל – צפייה והורדות")
    pwd = st.text_input("סיסמת מנהל:", type="password")
    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("התחברת בהצלחה ✅")
            df = load_df(CSV_FILE)
            if df.empty:
                st.info("אין עדיין נתונים בקובץ.")
            else:
                st.dataframe(df, use_container_width=True)
                with st.expander("📥 הורדות", expanded=True):
                    # הצגת כפתורי הורדה בעמודות מימין
                    col_spacer, col_excel, col_csv = st.columns([8,1,1], gap="small")

                    with col_excel:
                        st.download_button(
                            "📄 Excel – כל הנתונים",
                            data=df_to_excel_bytes(df),
                            file_name="שאלון_שיבוץ_כללי.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key="dl_excel_all"
                        )

                    with col_csv:
                        st.download_button(
                            "📄 CSV – כל הנתונים",
                            data=df.to_csv(index=False, encoding="utf-8-sig"),
                            file_name="שאלון_שיבוץ_כללי.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="dl_csv_all"
                        )

                    # חיזוק RTL ויישור לימין
                    st.markdown("""
                    <style>
                      .stExpander div[data-testid="stExpanderContent"] > div {
                        direction: rtl;
                        text-align: right;
                      }
                      [data-testid="stDownloadButton"] > div > button {
                        width: 100%;
                      }
                    </style>
                    """, unsafe_allow_html=True)
        else:
            st.error("סיסמה שגויה")
    st.stop()

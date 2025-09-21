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

CSV_FILE = DATA_DIR / "mapping_data.csv"          # קובץ ראשי (נשמר ומעודכן)
CSV_LOG_FILE = DATA_DIR / "mapping_data_log.csv"  # קובץ יומן הוספות (Append-Only)
SITES_FILE = DATA_DIR / "sites_catalog.csv"       # אופציונלי: קטלוג מוסדות/תחומים

# ===== רשימת תחומי התמחות =====
SPECIALIZATIONS = [
    "מערכות מידע רפואיות", "בריאות דיגיטלית", "רווחה", "חינוך", "קהילה",
    "סיעוד", "פסיכולוגיה קהילתית", "מנהל מערכות מידע", "ניתוח נתונים", "סיוע טכנולוגי",
    "אחר"
]

# ===== סדר עמודות רצוי =====
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
st.markdown("""<style> ... </style>""", unsafe_allow_html=True)

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

def save_master_row(row_df: pd.DataFrame) -> None:
    """שמירה מצטברת (Append-Only) של שורה חדשה אל הקובץ הראשי + גיבוי מתוארך"""
    row_df = reorder_columns(row_df.copy())
    file_exists = CSV_FILE.exists()
    row_df.to_csv(
        CSV_FILE,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8-sig"
    )
    try:
        df_all = load_csv_safely(CSV_FILE)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"mapping_data_{ts}.csv"
        df_all.to_csv(backup_path, index=False, encoding="utf-8-sig")
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

# ===== קריאת קטלוג מוסדות/תחומים =====
def load_sites_catalog():
    ...
sites_df = load_sites_catalog()
sites_available = not sites_df.empty

known_specs = sorted(sites_df['תחום התמחות'].dropna().unique().tolist()) if sites_available else SPECIALIZATIONS[:]
known_institutions = sorted(sites_df['מוסד'].dropna().unique().tolist()) if sites_available else []

# ===== מצב מנהל =====
params = st.query_params if hasattr(st, "query_params") else {}
admin_flag = params.get("admin", "0")
is_admin_mode = (admin_flag == "1")

if is_admin_mode:
    ...
    st.stop()

# ===== טופס למילוי =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו")
...
with st.form("mapping_form"):
    ...
    submit_btn = st.form_submit_button("שלח/י", use_container_width=True)

# ===== טיפול בטופס =====
if submit_btn:
    errors = []
    ...
    if errors:
        for e in errors:
            st.error(e)
    else:
        record = {...}
        new_row_df = pd.DataFrame([record])

        # שינוי כאן: לא טוענים את כל ה־master ושומרים מחדש,
        # אלא מוסיפים שורה לקובץ הראשי (Append-Only)
        save_master_row(new_row_df)
        append_to_log(new_row_df)

        st.success("✅ הנתונים נשמרו בהצלחה! תודה רבה 🙏")
        st.info("טיפ: ניתן לצפות/להוריד את הקבצים במצב מנהל ?admin=1 (עם הסיסמה).")

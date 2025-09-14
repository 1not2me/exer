# matcher_streamlit_rtl_csv_xlsx_v4.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# =========================
# עיצוב בסיסי + RTL
# =========================
st.markdown("""
<style>
@font-face {
  font-family:'David';
  src:url('https://example.com/David.ttf') format('truetype');
}
html, body, [class*="css"] {
  font-family:'David',sans-serif!important;
}

/* ====== עיצוב מודרני + RTL ====== */
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

/* כותרות */
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center;
  letter-spacing:.5px;
  text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}

/* כפתור */
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:18px!important;
  padding:1rem 2rem!important;
  font-size:1.1rem!important;
  font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important;
  transition:all .15s ease!important;
}
.stButton > button:hover{ transform:translateY(-3px) scale(1.02); filter:brightness(1.08); }
.stButton > button:focus{ outline:none!important; box-shadow:0 0 0 4px var(--ring)!important; }

/* קלטים */
div.stSelectbox > div,
div.stMultiSelect > div,
.stTextInput > div > div > input{
  border-radius:14px!important;
  border:1px solid rgba(15,23,42,.12)!important;
  box-shadow:0 3px 10px rgba(15,23,42,.04)!important;
  padding:.6rem .8rem!important;
  color:var(--ink)!important;
  font-size:1rem!important;
}

/* טאבים – רוחב קטן יותר */
.stTabs [data-baseweb="tab"]{
  border-radius:14px!important;
  background:rgba(255,255,255,.65);
  margin-inline-start:.3rem;
  padding:.4rem .8rem;
  font-weight:600;
  min-width: 110px !important;
  text-align:center;
  font-size:0.9rem !important;
}
.stTabs [data-baseweb="tab"]:hover{ background:rgba(255,255,255,.9); }

/* RTL */
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }

/* הסתרת טיפ "Press Enter to apply" */
*[title="Press Enter to apply"]{ display:none !important; }

/* ====== כפתורי הורדה – סגנון "פיל" ====== */
div.stDownloadButton{ direction:rtl; text-align:right; }
div.stDownloadButton > button{
  border:1px solid rgba(15,23,42,.12)!important;
  border-radius:999px!important;
  padding:.85rem 1.2rem!important;
  font-size:1.05rem!important;
  font-weight:600!important;
  background:#fff!important;
  color:#111!important;
  box-shadow:0 8px 18px rgba(15,23,42,.06)!important;
  display:inline-flex!important;
  align-items:center!important;
  gap:.5rem!important;
}
div.stDownloadButton > button:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 22px rgba(15,23,42,.08)!important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# מודל ניקוד
# =========================
@dataclass
class Weights:
    w_field: float = 0.70
    w_city: float = 0.20
    w_special: float = 0.10

W = Weights()

# מיפוי שמות עמודות אפשריים (בעברית) -> שדות פנימיים
STU_COLS = {
    "id": ["מספר תעודת זהות", "תעודת זהות", "ת\"ז", "תז", "תעודת זהות הסטודנט"],
    "first": ["שם פרטי"],
    "last": ["שם משפחה"],
    "address": ["כתובת", "כתובת הסטודנט", "רחוב"],
    "city": ["עיר מגורים", "עיר"],
    "phone": ["טלפון", "מספר טלפון"],
    "email": ["דוא\"ל", "דוא״ל", "אימייל", "כתובת אימייל", "כתובת מייל"],
    "preferred_field": ["תחום מועדף","תחומים מועדפים"],
    "special_req": ["בקשה מיוחדת"],
    "partner": ["בן/בת זוג להכשרה", "בן\\בת זוג להכשרה", "בן/בת זוג", "בן\\בת זוג"]
}
SITE_COLS = {
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות"],
    "field": ["תחום ההתמחות", "תחום התמחות"],
    "street": ["רחוב"],
    "city": ["עיר"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה", "מספר סטודנטים שניתן לקלוט", "קיבולת"],
    "sup_first": ["שם פרטי"],
    "sup_last": ["שם משפחה"],
    "phone": ["טלפון"],
    "email": ["אימייל", "כתובת מייל", "דוא\"ל", "דוא״ל"]
}

# =========================
# עזרי קריאה בטוחים
# =========================
def read_csv_robust(uploaded) -> Optional[pd.DataFrame]:
    """
    מנסה כמה קידודים נפוצים לעברית כדי למנוע שגיאות.
    """
    encodings = ["utf-8-sig", "utf-8", "cp1255", "iso-8859-8"]
    last_err = None
    for enc in encodings:
        try:
            uploaded.seek(0)
            return pd.read_csv(uploaded, encoding=enc)
        except Exception as e:
            last_err = e
            continue
    st.error(f"שגיאת קריאת CSV: {last_err}")
    return None

def read_excel_robust(uploaded) -> Optional[pd.DataFrame]:
    """
    קורא את הגליון הראשון. אם יש צורך בגליון ספציפי – אפשר להרחיב כאן.
    """
    try:
        uploaded.seek(0)
        return pd.read_excel(uploaded)  # pandas יזהה engine מתאים (openpyxl/xlrd)
    except Exception as e:
        st.error(f"שגיאת קריאת Excel: {e}")
        return None

def read_any(uploaded) -> Optional[pd.DataFrame]:
    """
    קורא CSV/XLSX/XLS בצורה יציבה. מחזיר None אם נכשל.
    """
    if uploaded is None:
        return None
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return read_csv_robust(uploaded)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return read_excel_robust(uploaded)

    # ניסיון גיבוי: קודם Excel אח"כ CSV
    df = read_excel_robust(uploaded)
    if df is not None:
        return df
    return read_csv_robust(uploaded)

def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns:
            return opt
    return None

def normalize_text(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()

def series_or_default(df: pd.DataFrame, options: List[str], default: str = "") -> pd.Series:
    col = pick_col(df, options)
    if col is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[col].fillna(default).astype(str)

def numeric_series_or_default(df: pd.DataFrame, options: List[str], default: int = 1) -> pd.Series:
    col = pick_col(df, options)
    if col is None:
        return pd.Series([default] * len(df), index=df.index, dtype=int)
    return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(int)

# =========================
# עיבוד נתוני קלט
# =========================
def detect_site_type(name: str, field: str) -> str:
    text = f"{name or ''} {field or ''}".replace("־"," ").replace("-"," ").lower()
    pairs = [("כלא","כלא"),("בית סוהר","כלא"),
             ("בית חולים","בית חולים"),("מרכז רפואי","בית חולים"),
             ("מרפאה","בריאות"),
             ("בי\"ס","בית ספר"),("בית ספר","בית ספר"),("תיכון","בית ספר"),
             ("גן","גן ילדים"),
             ("מרכז קהילתי","קהילה"),("רווחה","רווחה"),
             ("חוסן","בריאות הנפש"),("בריאות הנפש","בריאות הנפש")]
    for k,v in pairs:
        if k in text:
            return v
    if "חינוך" in (field or ""):
        return "חינוך"
    return "אחר"

def resolve_students(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=[
            "stu_id","stu_first","stu_last","stu_phone","stu_email",
            "stu_city","stu_address","stu_pref","stu_req","stu_partner"
        ])
    out = df.copy()
    out["stu_id"]      = series_or_default(out, STU_COLS["id"])
    out["stu_first"]   = series_or_default(out, STU_COLS["first"])
    out["stu_last"]    = series_or_default(out, STU_COLS["last"])
    out["stu_phone"]   = series_or_default(out, STU_COLS["phone"])
    out["stu_email"]   = series_or_default(out, STU_COLS["email"])
    out["stu_city"]    = series_or_default(out, STU_COLS["city"])
    out["stu_address"] = series_or_default(out, STU_COLS["address"])
    out["stu_pref"]    = series_or_default(out, STU_COLS["preferred_field"])
    out["stu_req"]     = series_or_default(out, STU_COLS["special_req"])
    out["stu_partner"] = series_or_default(out, STU_COLS["partner"])

    for c in ["stu_id","stu_first","stu_last","stu_phone","stu_email","stu_city","stu_address","stu_pref","stu_req","stu_partner"]:
        out[c] = out[c].apply(normalize_text)
    return out

def resolve_sites(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=[
            "site_name","site_field","site_street","site_city",
            "site_capacity","capacity_left","site_type","supervisor"
        ])
    out = df.copy()
    out["site_name"]     = series_or_default(out, SITE_COLS["name"])
    out["site_field"]    = series_or_default(out, SITE_COLS["field"])
    out["site_street"]   = series_or_default(out, SITE_COLS["street"])
    out["site_city"]     = series_or_default(out, SITE_COLS["city"])
    out["site_capacity"] = numeric_series_or_default(out, SITE_COLS["capacity"], default=1).clip(lower=0).astype(int)
    out["capacity_left"] = out["site_capacity"].astype(int)

    # טיפוס מקום (עמיד לריקים)
    out["site_type"] = (out["site_name"].astype(str) + " || " + out["site_field"].astype(str)).apply(
        lambda s: detect_site_type(*s.split(" || ", 1))
    )

    # שם מדריך (אם יש)
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    if sup_first or sup_last:
        ff = out[sup_first].astype(str) if sup_first else ""
        ll = out[sup_last].astype(str)  if sup_last  else ""
        out["supervisor"] = (ff + " " + ll).str.strip()
    else:
        out["supervisor"] = ""

    for c in ["site_name","site_field","site_street","site_city","site_type","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

# =========================
# חישוב ניקוד ושיבוץ
# =========================
def tokens(s: str) -> List[str]:
    return [t for t in str(s).replace(","," ").replace("/"," ").replace("-"," ").split() if t]

def field_match_score(stu_pref: str, site_field: str) -> float:
    if not stu_pref:
        return 50.0
    sp = stu_pref.strip()
    sf = (site_field or "").strip()
    if not sf:
        return 40.0
    if sp and sp in sf:
        return 90.0
    tp = set([w for w in tokens(sp) if len(w) > 1])
    tf = set([w for w in tokens(sf) if len(w) > 1])
    if tp.intersection(tf):
        return 75.0
    return 45.0

def special_req_score(req: str, site_type: str, same_city: bool) -> float:
    if not req:
        return 70.0
    if "לא בבית חולים" in req and site_type == "בית חולים":
        return 0.0
    if "קרוב" in req:
        return 90.0 if same_city else 55.0
    return 75.0

def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = bool(stu.get("stu_city")) and bool(site.get("site_city")) and (stu.get("stu_city") == site.get("site_city"))
    field_s   = field_match_score(stu.get("stu_pref",""), site.get("site_field",""))
    city_s    = 100.0 if same_city else 65.0
    special_s = special_req_score(stu.get("stu_req",""), site.get("site_type",""), same_city)
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

def find_partner_map(students_df: pd.DataFrame) -> Dict[str,str]:
    if students_df.empty:
        return {}
    ids = set(students_df["stu_id"])
    m: Dict[str,str] = {}
    for _, r in students_df.iterrows():
        sid = r.get("stu_id","")
        pid = r.get("stu_partner","")
        if not sid or not pid:
            continue
        if pid in ids and pid != sid:
            m[sid] = pid
            continue
        for _, r2 in students_df.iterrows():
            full = f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and full and pid in full and r2.get("stu_id","") != sid:
                m[sid] = r2.get("stu_id","")
                break
    return m

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    if sites_df.empty:
        return pd.DataFrame(columns=list(sites_df.columns) + ["score"])
    tmp = sites_df.copy()
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, W), axis=1)
    return tmp.sort_values(["score"], ascending=[False])

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    """
    מחזיר טבלת תוצאה בעברית לכל הסטודנטים (כולל מי שלא שובץ).
    """
    if students_df is None or sites_df is None or students_df.empty:
        return pd.DataFrame(columns=[
            "ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר",
            "מספר טלפון","אימייל","אחוז התאמה","שם מקום ההתמחות",
            "עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"
        ])

    # ודא שדה קיבולת
    if "capacity_left" not in sites_df.columns:
        sites_df = sites_df.copy()
        if "site_capacity" in sites_df.columns:
            sites_df["capacity_left"] = sites_df["site_capacity"].astype(int)
        else:
            sites_df["capacity_left"] = 1

    separate_couples = True
    top_k = 10

    def dec_cap(idx: int):
        sites_df.at[idx, "capacity_left"] = max(0, int(sites_df.at[idx, "capacity_left"]) - 1)

    results: List[Tuple[pd.Series, Optional[pd.Series]]] = []
    processed = set()
    partner_map = find_partner_map(students_df)

    # שיבוץ זוגות (אם אפשר לשבץ את שניהם)
    for _, s in students_df.iterrows():
        sid = s.get("stu_id","")
        if not sid or sid in processed:
            continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"] == pid]
            if partner_row.empty:
                continue
            s2 = partner_row.iloc[0]
            avail = sites_df[sites_df["capacity_left"] > 0]
            cand1 = candidate_table_for_student(s, avail, W).head(top_k)
            cand2 = candidate_table_for_student(s2, avail, W).head(top_k)
            best = (-1.0, None, None)
            for i1, r1 in cand1.iterrows():
                for i2, r2 in cand2.iterrows():
                    if i1 == i2:
                        continue
                    if separate_couples and r1.get("supervisor") and r1.get("supervisor") == r2.get("supervisor"):
                        continue
                    sc = float(r1["score"]) + float(r2["score"])
                    if sc > best[0]:
                        best = (sc, i1, i2)
            if best[1] is not None and best[2] is not None:
                rsite1 = sites_df.loc[best[1]]
                rsite2 = sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s, rsite1))
                results.append((s2, rsite2))
                processed.add(sid); processed.add(pid)

    # שיבוץ בודדים/מי שלא שובץ עדיין
    for _, s in students_df.iterrows():
        sid = s.get("stu_id","")
        if not sid or sid in processed:
            continue
        avail = sites_df[sites_df["capacity_left"] > 0]
        cand = candidate_table_for_student(s, avail, W).head(top_k)
        if not cand.empty:
            chosen_idx = cand.index[0]
            rsite = sites_df.loc[chosen_idx]
            dec_cap(chosen_idx)
            results.append((s, rsite))
            processed.add(sid)
        else:
            results.append((s, None))
            processed.add(sid)

    # בניית פלט בעברית
    rows = []
    for s, r in results:
        if r is None:
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id",""),
                "שם פרטי": s.get("stu_first",""),
                "שם משפחה": s.get("stu_last",""),
                "כתובת": s.get("stu_address",""),
                "עיר": s.get("stu_city",""),
                "מספר טלפון": s.get("stu_phone",""),
                "אימייל": s.get("stu_email",""),
                "אחוז התאמה": 0.0,
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "סוג מקום השיבוץ": "",
                "תחום ההתמחות במוסד": "",
            })
        else:
            score = compute_score(s, r, W)
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id",""),
                "שם פרטי": s.get("stu_first",""),
                "שם משפחה": s.get("stu_last",""),
                "כתובת": s.get("stu_address",""),
                "עיר": s.get("stu_city",""),
                "מספר טלפון": s.get("stu_phone",""),
                "אימייל": s.get("stu_email",""),
                "אחוז התאמה": round(score, 1),
                "שם מקום ההתמחות": r.get("site_name",""),
                "עיר המוסד": r.get("site_city",""),
                "סוג מקום השיבוץ": r.get("site_type",""),
                "תחום ההתמחות במוסד": r.get("site_field",""),
            })
    out = pd.DataFrame(rows)
    desired = ["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר","מספר טלפון","אימייל",
               "אחוז התאמה","שם מקום ההתמחות","עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"]
    remaining = [c for c in out.columns if c not in desired]
    return out[[c for c in desired if c in out.columns] + remaining]

# =========================
# UI – העלאת קבצים והרצה
# =========================
colA, colB = st.columns(2)
with colA:
    students_file = st.file_uploader("קובץ סטודנטים (CSV/XLSX)", type=["csv","xlsx","xls"], key="students_file")
with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים (CSV/XLSX)", type=["csv","xlsx","xls"], key="sites_file")

df_students_raw = None
df_sites_raw = None

if students_file is not None:
    df_students_raw = read_any(students_file)
    if isinstance(df_students_raw, pd.DataFrame) and not df_students_raw.empty:
        st.success("קובץ הסטודנטים נקרא בהצלחה.")
        st.dataframe(df_students_raw.head(5), use_container_width=True)
    else:
        st.error("לא ניתן לקרוא את קובץ הסטודנטים. ודא/י פורמט ונתונים תקינים.")

if sites_file is not None:
    df_sites_raw = read_any(sites_file)
    if isinstance(df_sites_raw, pd.DataFrame) and not df_sites_raw.empty:
        st.success("קובץ האתרים/מדריכים נקרא בהצלחה.")
        st.dataframe(df_sites_raw.head(5), use_container_width=True)
    else:
        st.error("לא ניתן לקרוא את קובץ האתרים/מדריכים. ודא/י פורמט ונתונים תקינים.")

st.markdown("---")
run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

result_df = None
if run_btn:
    if df_students_raw is None or df_students_raw.empty or df_sites_raw is None or df_sites_raw.empty:
        st.error("יש בעיה בקריאת אחד הקבצים. נא לתקן ולנסות שוב.")
    else:
        try:
            students = resolve_students(df_students_raw)
            sites = resolve_sites(df_sites_raw)
            result_df = greedy_match(students, sites, W)
            st.success("השיבוץ הושלם ✓")
        except Exception as e:
            st.exception(e)

# =========================
# תוצאות + הורדות בעברית (CSV/XLSX)
# =========================
if result_df is not None and not result_df.empty:
    st.markdown("## 📊 תוצאות השיבוץ")
    st.dataframe(result_df, use_container_width=True)

    # --- הורדה: CSV בעברית (UTF-8-SIG כדי שייפתח יפה באקסל) ---
    csv_bytes = result_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ הורדת תוצאות כ-CSV (עברית)",
        data=csv_bytes,
        file_name="student_site_matching_hebrew.csv",
        mime="text/csv",
        key="dl_csv_he"
    )

    # --- הורדה: XLSX בעברית + RTL ---
    xlsx_io = BytesIO()
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        sheet_name = "שיבוץ"
        result_df.to_excel(writer, index=False, sheet_name=sheet_name)

        # עיצוב ימין-שמאל + הדגשת כותרות
        workbook  = writer.book
        worksheet = writer.sheets[sheet_name]
        try:
            worksheet.right_to_left()  # הופך את הגליון לימין־לשמאל
        except Exception:
            pass

        # עיצוב כותרת: מודגש + יישור לימין
        header_fmt = workbook.add_format({"bold": True, "align": "right"})
        for col_num, value in enumerate(result_df.columns.tolist()):
            worksheet.write(0, col_num, value, header_fmt)
            # הרחבת עמודות בצורה סבירה
            width = min(35, max(12, int(result_df[value].astype(str).str.len().mean() + 4)))
            worksheet.set_column(col_num, col_num, width)

        # יישור טקסט תא לימין
        body_fmt = workbook.add_format({"align": "right"})
        # החלת היישור לכל הטווח עם set_column (פורמט ברירת מחדל)
        worksheet.set_column(0, len(result_df.columns)-1, None, body_fmt)

    xlsx_io.seek(0)
    st.download_button(
        "⬇️ הורדת תוצאות כ-Excel (עברית, RTL)",
        data=xlsx_io.getvalue(),
        file_name="student_site_matching_hebrew.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_xlsx_he"
    )
else:
    st.caption("טרם הופעל שיבוץ או שאין תוצאות להצגה.")

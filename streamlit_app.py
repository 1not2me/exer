# matcher_streamlit_beauty_rtl_v7_fixed.py
# -*- coding: utf-8 -*-
import re
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Any, List
from math import radians, sin, cos, sqrt, atan2

# =========================
# קונפיגורציה כללית
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב מודרני + RTL ======
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;600&display=swap');

html, body, [class*="css"] { 
  font-family: 'Rubik', 'David', sans-serif !important; 
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
  letter-spacing:.5px;
  text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}

.stButton > button,
div[data-testid="stDownloadButton"] > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:18px!important;
  padding:1rem 2rem!important;
  font-size:1.1rem!important;
  font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important;
  transition:all .15s ease!important;
  width:100% !important;
}
.stButton > button:hover,
div[data-testid="stDownloadButton"] > button:hover{ 
  transform:translateY(-3px) scale(1.02); 
  filter:brightness(1.08); 
}
.stButton > button:focus,
div[data-testid="stDownloadButton"] > button:focus{ 
  outline:none!important; 
  box-shadow:0 0 0 4px var(--ring)!important; 
}

.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>כאן משבצים סטודנטים למקומות התמחות בקלות, בהתבסס על תחום, עיר ובקשות.</p>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float = 0.50   # 50%
    w_city: float = 0.05    # 5% (עד 5 נק')
    w_special: float = 0.45 # 45%

MIN_SCORE = 20  # ציון מינימלי לפי בקשתך

# עמודות סטודנטים
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

# עמודות אתרים
SITE_COLS = {
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות", "שם המוסד", "מוסד ההכשרה"],
    "field": ["תחום ההתמחות", "תחום התמחות"],
    "street": ["רחוב"],
    "city": ["עיר"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה", "מספר סטודנטים שניתן לקלוט", "קיבולת"],
    "sup_first": ["שם פרטי"],
    "sup_last": ["שם משפחה"],
    "phone": ["טלפון"],
    "email": ["אימייל", "כתובת מייל", "דוא\"ל", "דוא״ל"],
    "review": ["חוות דעת מדריך"],
    # ננסה לאתר עמודת "בקשות מיוחדות" אם קיימת בקובץ האתרים
    "special": ["בקשות מיוחדות", "בקשה מיוחדת", "דרישות מיוחדות"]
}

def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns: return opt
    return None

# ----- קריאת קבצים -----
def read_any(uploaded) -> pd.DataFrame:
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")
    if name.endswith((".xlsx",".xls")):
        return pd.read_excel(uploaded)
    return pd.read_csv(uploaded, encoding="utf-8-sig")

def normalize_text(x: Any) -> str:
    if x is None: return ""
    return str(x).strip()

# ===== חילוץ עיר מהכתובת (אם אין עמודת "עיר") =====
def extract_city(address: str) -> str:
    if pd.isna(address):
        return ""
    address = str(address).strip()
    parts = re.split(r'[,|/|-]', address)
    if len(parts) > 1:
        return parts[-1].strip()
    toks = address.split()
    return toks[-1].strip() if toks else ""

# ----- סטודנטים -----
def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stu_id"]    = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]

    city_col = pick_col(out, STU_COLS["city"])
    if city_col:
        out["stu_city"] = out[city_col]
    else:
        addr_col = pick_col(out, STU_COLS["address"])
        out["stu_city"] = out[addr_col].apply(extract_city) if addr_col else ""

    pref_col = pick_col(out, STU_COLS["preferred_field"])
    req_col  = pick_col(out, STU_COLS["special_req"])
    out["stu_pref"] = out[pref_col] if pref_col else ""
    out["stu_req"]  = out[req_col]  if req_col  else ""

    for c in ["stu_id","stu_first","stu_last","stu_city","stu_pref","stu_req"]:
        out[c] = out[c].apply(normalize_text)
    return out

# ----- אתרים -----
def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_name"]  = out[pick_col(out, SITE_COLS["name"])]
    out["site_field"] = out[pick_col(out, SITE_COLS["field"])]
    out["site_city"]  = out[pick_col(out, SITE_COLS["city"])]

    cap_col = pick_col(out, SITE_COLS["capacity"])
    out["site_capacity"] = pd.to_numeric(out[cap_col], errors="coerce").fillna(1).astype(int) if cap_col else 1
    out["capacity_left"] = out["site_capacity"].astype(int)

    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["שם המדריך"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last else ""
        out["שם המדריך"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()

    special_col = pick_col(out, SITE_COLS["special"])
    out["site_special"] = out[special_col] if special_col else ""

    for c in ["site_name","site_field","site_city","site_special","שם המדריך"]:
        out[c] = out[c].apply(normalize_text)
    return out

# ===== רשימת קואורדינטות ערים בישראל (ניתן להרחיב כרצונך) =====
cities_coords = {
    "תל אביב": (32.0853, 34.7818),
    "ירושלים": (31.7683, 35.2137),
    "חיפה": (32.7940, 34.9896),
    "רמת גן": (32.0684, 34.8248),
    "גבעתיים": (32.0700, 34.8089),
    "בת ים": (32.0171, 34.7454),
    "חולון": (32.0158, 34.7874),
    "פתח תקווה": (32.0840, 34.8878),
    "ראשון לציון": (31.9710, 34.7894),
    "רחובות": (31.8948, 34.8113),
    "נתניה": (32.3215, 34.8532),
    "הרצליה": (32.1663, 34.8439),
    "מודיעין": (31.8980, 35.0104),
    "אשדוד": (31.8014, 34.6436),
    "באר שבע": (31.2520, 34.7915),
    "עכו": (32.9234, 35.0827),
    "נהריה": (33.0058, 35.0940),
    "כרמיאל": (32.9171, 35.3050),
    "צפת": (32.9646, 35.4960),
    "נוף הגליל": (32.7019, 35.3033),
    "טבריה": (32.7922, 35.5312),
    "גוליס": (33.0330, 35.3160),  # יישוב קטן לדוגמה
}

# ===== פונקציות מרחק בין ערים =====
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # ק"מ
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def city_distance_km(city1: str, city2: str) -> Optional[float]:
    city1 = (city1 or "").strip()
    city2 = (city2 or "").strip()
    if not city1 or not city2:
        return None
    if city1 == city2:
        return 0.0
    if city1 not in cities_coords or city2 not in cities_coords:
        return None
    lat1, lon1 = cities_coords[city1]
    lat2, lon2 = cities_coords[city2]
    return haversine(lat1, lon1, lat2, lon2)

# ====== חישוב ציון מדויק לפי המשקולות ======
def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    # נוודא מחרוזות נקיות
    stu_pref = str(stu.get("stu_pref", "")).strip()
    site_field = str(site.get("site_field", "")).strip()
    stu_req  = str(stu.get("stu_req", "")).strip()
    site_special = str(site.get("site_special", "")).strip()
    stu_city = str(stu.get("stu_city", "")).strip()
    site_city = str(site.get("site_city", "")).strip()

    # 1) תחום (0/50)
    field_score = 50 if (stu_pref and site_field and (stu_pref in site_field)) else 0

    # 2) עיר (0..5 לפי מרחק)
    city_score = 0
    if stu_city and site_city:
        dist = city_distance_km(stu_city, site_city)
        if dist is None:
            # לא ידועים קואורדינטות: ניתן ניקוד מלא אם זהות מילולית
            city_score = 5 if (stu_city == site_city) else 0
        else:
            if dist <= 5:
                city_score = 5
            elif dist <= 20:
                city_score = 3
            elif dist <= 50:
                city_score = 1
            else:
                city_score = 0

    # 3) בקשה מיוחדת (0/45)
    # לוגיקה:
    #   - אם הסטודנט כתב "קרוב" / "קרבה" → נדרוש קרבה מרחקית (dist<=20) כדי לתת 45.
    #   - אחרת ננסה התאמת טקסט פשוטה בין הבקשה לטקסט של המוסד (site_special / field / name).
    special_score = 0
    if stu_req:
        req = stu_req
        near_words = ["קרוב", "קרבה", "סמוך", "בסביבה", "ליד"]
        if any(w in req for w in near_words):
            # נסתמך על city_score שנגזר מהמרחק: 3/5 מצביע על קרבה מספקת
            if city_score >= 3:
                special_score = 45
        else:
            haystack = " ".join([site_special, site_field, str(site.get("site_name","")), site_city]).strip()
            if haystack and req and (req in haystack):
                special_score = 45

    # סכימה סופית
    total = field_score + special_score + city_score

    # ציון מינימום
    total = max(total, MIN_SCORE)

    # קלמפ בין 0 ל-100 (למקרה של שינויים עתידיים)
    return float(np.clip(total, 0, 100))

# ====== שיבוץ ======
def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    results = []
    supervisor_count = {}

    for _, s in students_df.iterrows():
        cand = sites_df[sites_df["capacity_left"] > 0].copy()
        if cand.empty:
            results.append({
                "ת\"ז הסטודנט": s["stu_id"],
                "שם פרטי": s["stu_first"],
                "שם משפחה": s["stu_last"],
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "תחום ההתמחות במוסד": "",
                "שם המדריך": "",
                "אחוז התאמה": MIN_SCORE  # גם כשאין, נשמור מינימום
            })
            continue

        # מחשב לכל אתר ציון התאמה לפי הנוסחה
        cand["score"] = cand.apply(lambda r: compute_score(s, r, W), axis=1)

        # מגבלה: עד 2 סטודנטים לכל מדריך
        cand = cand[cand.apply(lambda r: supervisor_count.get(r.get("שם המדריך",""),0) < 2, axis=1)]

        if cand.empty:
            results.append({
                "ת\"ז הסטודנט": s["stu_id"],
                "שם פרטי": s["stu_first"],
                "שם משפחה": s["stu_last"],
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "תחום ההתמחות במוסד": "",
                "שם המדריך": "",
                "אחוז התאמה": MIN_SCORE
            })
            continue

        chosen = cand.sort_values("score", ascending=False).iloc[0]
        idx = chosen.name
        sites_df.at[idx, "capacity_left"] -= 1

        sup_name = chosen.get("שם המדריך", "")
        supervisor_count[sup_name] = supervisor_count.get(sup_name, 0) + 1

        results.append({
            "ת\"ז הסטודנט": s["stu_id"],
            "שם פרטי": s["stu_first"],
            "שם משפחה": s["stu_last"],
            "שם מקום ההתמחות": chosen["site_name"],
            "עיר המוסד": chosen.get("site_city", ""),
            "תחום ההתמחות במוסד": chosen["site_field"],
            "שם המדריך": sup_name,
            "אחוז התאמה": round(float(chosen["score"]), 1)
        })

    return pd.DataFrame(results)

# =========================
# 1) הוראות שימוש
# =========================
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל.  
   אופציונלי: תחום מועדף/תחומים מועדפים, בקשה מיוחדת, בן/בת זוג להכשרה.  
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה, מדריך, (אופציונלי) בקשות מיוחדות/חוות דעת.  
3. לחצו **בצע שיבוץ** – המערכת מחשבת *אחוז התאמה* לפי תחום (50%), בקשות מיוחדות (45%), עיר (5%, לפי מרחק).  
4. בסוף אפשר להוריד **XLSX** של התוצאות ושל סיכום לפי מוסד. 
""")

# =========================
# 2) דוגמה לשימוש
# =========================
st.markdown("## 🧪 דוגמה לשימוש")
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחום מועדף":"בריאות הנפש", "בקשה מיוחדת":"קרוב לבית"},
    {"שם פרטי":"יואב", "שם משפחה":"לוי", "תעודת זהות":"987654321", "עיר מגורים":"חיפה", "טלפון":"0502222222", "דוא\"ל":"yoav@example.com", "תחום מועדף":"רווחה"},
    {"שם פרטי":"סמאח", "שם משפחה":"ח'ורי", "תעודת זהות":"456789123", "עיר מגורים":"עכו", "טלפון":"0503333333", "דוא\"ל":"sama@example.com", "תחום מועדף":"חינוך מיוחד"},
])
example_sites = pd.DataFrame([
    {"מוסד / שירות הכשרה":"מרכז חוסן תל אביב", "תחום ההתמחות":"בריאות הנפש", "עיר":"תל אביב", "מספר סטודנטים שניתן לקלוט השנה":2, "שם פרטי":"דניאל", "שם משפחה":"כהן", "חוות דעת מדריך":"מדריך מצוין"},
    {"מוסד / שירות הכשרה":"מחלקת רווחה חיפה", "תחום ההתמחות":"רווחה", "עיר":"חיפה", "מספר סטודנטים שניתן לקלוט השנה":1, "שם פרטי":"מיכל", "שם משפחה":"לוי", "חוות דעת מדריך":"זקוקה לשיפור"},
    {"מוסד / שירות הכשרה":"בית ספר יד לבנים", "תחום ההתמחות":"חינוך מיוחד", "עיר":"עכו", "מספר סטודנטים שניתן לקלוט השנה":1, "שם פרטי":"שרה", "שם משפחה":"כהן"},
])
colX, colY = st.columns(2, gap="large")
with colX:
    st.write("**דוגמה – סטודנטים**")
    st.dataframe(example_students, use_container_width=True)
with colY:
    st.write("**דוגמה – אתרי התמחות/מדריכים**")
    st.dataframe(example_sites, use_container_width=True)

# =========================
# 3) העלאת קבצים
# =========================
st.markdown("## 📤 העלאת קבצים")
colA, colB = st.columns(2, gap="large")

with colA:
    students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="students_file")
    if students_file is not None:
        try:
            st.session_state["df_students_raw"] = read_any(students_file)
            st.dataframe(st.session_state["df_students_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ הסטודנטים: {e}")

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        try:
            st.session_state["df_sites_raw"] = read_any(sites_file)
            st.dataframe(st.session_state["df_sites_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ האתרים/מדריכים: {e}")

for k in ["df_students_raw","df_sites_raw","result_df"]:
    st.session_state.setdefault(k, None)

# ---- יצירת XLSX ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    import xlsxwriter
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        cols = list(df.columns)
        has_match_col = "אחוז התאמה" in cols
        if has_match_col:
            cols = [c for c in cols if c != "אחוז התאמה"] + ["אחוז התאמה"]

        df[cols].to_excel(writer, index=False, sheet_name=sheet_name)

        if has_match_col:
            workbook  = writer.book
            worksheet = writer.sheets[sheet_name]
            red_fmt = workbook.add_format({"font_color": "red"})
            col_idx = len(cols) - 1
            worksheet.set_column(col_idx, col_idx, 12, red_fmt)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

# =========================
# שיבוץ והצגת תוצאות
# =========================
if "result_df" not in st.session_state:
    st.session_state["result_df"] = None

st.markdown("## ⚙️ ביצוע השיבוץ")
if st.button("🚀 בצע שיבוץ", use_container_width=True):
    try:
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.markdown("## 📊 תוצאות השיבוץ")

    df_show = st.session_state["result_df"].copy()

    # העברת תחום ההתמחות אחרי שם מקום ההתמחות
    cols = list(df_show.columns)
    if "תחום ההתמחות במוסד" in cols and "שם מקום ההתמחות" in cols:
        cols.insert(cols.index("שם מקום ההתמחות")+1, cols.pop(cols.index("תחום ההתמחות במוסד")))
        df_show = df_show[cols]

    st.dataframe(df_show, use_container_width=True)

    # הורדת קובץ תוצאות
    xlsx_results = df_to_xlsx_bytes(df_show, sheet_name="תוצאות")
    st.download_button("⬇️ הורדת XLSX – תוצאות השיבוץ", data=xlsx_results,
        file_name="student_site_matching.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- טבלת סיכום ---
    summary_df = (
        st.session_state["result_df"]
        .groupby(["שם מקום ההתמחות","תחום ההתמחות במוסד","שם המדריך"])
        .agg({
            "ת\"ז הסטודנט":"count",
            "שם פרטי": list,
            "שם משפחה": list
        }).reset_index()
    )
    summary_df.rename(columns={"ת\"ז הסטודנט":"כמה סטודנטים"}, inplace=True)

    # המלצת שיבוץ – שם מלא
    summary_df["המלצת שיבוץ"] = summary_df.apply(
        lambda row: " + ".join([f"{f} {l}" for f, l in zip(row["שם פרטי"], row["שם משפחה"])]),
        axis=1
    )

    summary_df = summary_df[[
        "שם מקום ההתמחות",
        "תחום ההתמחות במוסד",
        "שם המדריך",
        "כמה סטודנטים",
        "המלצת שיבוץ"
    ]]

    st.markdown("### 📝 טבלת סיכום לפי מקום הכשרה")
    st.dataframe(summary_df, use_container_width=True)

    xlsx_summary = df_to_xlsx_bytes(summary_df, sheet_name="סיכום")
    st.download_button("⬇️ הורדת XLSX – טבלת סיכום", data=xlsx_summary,
        file_name="student_site_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

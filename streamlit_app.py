# ===== בתחילת הקובץ: בדיקת זמינות openpyxl =====
try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False

# ... שאר הייבואים נשארים ...

# ===== עזר: כתיבה אטומית + גיבוי =====
def atomic_write_csv(df: pd.DataFrame, path: Path):
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)
    df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
    shutil.move(tmp_path, path)

def to_excel_rtl(df: pd.DataFrame, file_path: Path) -> bytes:
    """
    יוצר XLSX עם RTL אם openpyxl זמינה.
    אם לא — מעלה ValueError כדי שנתפוס למטה ולא נקרוס.
    """
    if not HAS_OPENPYXL:
        raise ValueError("openpyxl לא מותקנת — יצוא XLSX מבוטל. נא להשתמש ב-CSV או להתקין openpyxl.")

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="מיפוי")
        ws = writer.book["מיפוי"]
        ws.sheet_view.rightToLeft = True
        ws.freeze_panes = "A2"
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(12, max_len + 2), 40)
    return file_path.read_bytes()

def make_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    החזרת XLSX ל'הורדה' אם openpyxl זמינה; אחרת מעלה ValueError.
    """
    if not HAS_OPENPYXL:
        raise ValueError("openpyxl לא מותקנת — יצוא XLSX מבוטל. נא להשתמש ב-CSV או להתקין openpyxl.")

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

def save_persistent(new_rows: pd.DataFrame):
    """
    מוסיף שורות חדשות, משמר היסטוריה, יוצר גיבוי:
    - תמיד CSV מצטבר (atomic).
    - גיבוי XLSX ייווצר רק אם openpyxl זמינה; אחרת נשמור גיבוי CSV עם חותמת זמן.
    """
    if CSV_FILE.exists():
        existing = pd.read_csv(CSV_FILE)
    else:
        existing = pd.DataFrame(columns=COLUMNS)

    for c in COLUMNS:
        if c not in existing.columns:
            existing[c] = ""
        if c not in new_rows.columns:
            new_rows[c] = ""

    existing = existing[COLUMNS]
    new_rows = new_rows[COLUMNS]
    combined = pd.concat([existing, new_rows], ignore_index=True)

    # כתיבה אטומית ל-CSV
    atomic_write_csv(combined, CSV_FILE)

    # גיבוי
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if HAS_OPENPYXL:
        backup_xlsx = BACKUP_DIR / f"mapping_backup_{timestamp}.xlsx"
        try:
            to_excel_rtl(combined, backup_xlsx)
        except Exception as e:
            # אם נכשל מסיבה אחרת — ניפול לגיבוי CSV
            backup_csv = BACKUP_DIR / f"mapping_backup_{timestamp}.csv"
            atomic_write_csv(combined, backup_csv)
    else:
        backup_csv = BACKUP_DIR / f"mapping_backup_{timestamp}.csv"
        atomic_write_csv(combined, backup_csv)

    return combined

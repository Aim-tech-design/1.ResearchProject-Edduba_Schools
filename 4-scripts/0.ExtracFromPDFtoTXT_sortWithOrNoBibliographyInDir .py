import re
import shutil
from pathlib import Path
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent

PDF_INPUT_DIR = BASE_DIR / "edubbaData" / "edubba1_DataPDF" / "1.Articles"
TXT_RAW_DIR = (
    BASE_DIR
    / "edubbaData"
    / "edubba2.0_DataTxtRaw"
    / "2.0.datacollectTXT_AnchorArticles"
)
TXT_COPY_DIR = BASE_DIR / "edubbaData" / "edubba2.0_OriginalTxtCopy"

TXT_WITH_BIB_DIR = (
    BASE_DIR
    / "edubbaData"
    / "edubba2.0_DataTxtRaw"
    / "2.1.filterTxtWithBibliography_ForAnystyle"
)
TXT_NO_BIB_DIR = (
    BASE_DIR / "edubbaData" / "edubba2.0_DataTxtRaw" / "2.2.txtnoBibliography"
)

# TEXT NORMALIZATION CONFIG
norm_cfg = {
    "remove_hyphenation": True,
    "remove_line_breaks": True,
    "remove_control_symbols": True,
}

LANG_OCR = "eng"

# BIBLIOGRAPHY PATTERNS
BIBLIO_PATTERNS = [
    r"\nreferences\s*\n",
    r"\nbibliography\s*\n",
    r"\nreference list\s*\n",
    r"\nworks cited\s*\n",
    r"\nliterature cited\s*\n",
    r"\nsources\s*\n",
]


def ensure_dirs():
    TXT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    TXT_COPY_DIR.mkdir(parents=True, exist_ok=True)
    TXT_WITH_BIB_DIR.mkdir(parents=True, exist_ok=True)
    TXT_NO_BIB_DIR.mkdir(parents=True, exist_ok=True)


# PDF TEXT EXTRACTION
def extract_text_pdfplumber(pdf_path: Path) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text.strip()


def extract_text_ocr(pdf_path: Path, max_pages=50) -> str:
    text = ""
    pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=max_pages)

    for page in pages:
        t = pytesseract.image_to_string(page, lang=LANG_OCR)

        if norm_cfg["remove_hyphenation"]:
            t = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", t)

        if norm_cfg["remove_line_breaks"]:
            t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)

        if norm_cfg["remove_control_symbols"]:
            t = t.replace("\x0c", "")

        text += t + "\n\n"

    return text.strip()


def extract_text_auto(pdf_path: Path) -> str:
    text = extract_text_pdfplumber(pdf_path)
    if len(text) < 50:
        text = extract_text_ocr(pdf_path)
    return text


# BIBLIOGRAPHY EXTRACTION
def extract_bibliography(text: str) -> str:
    for pat in BIBLIO_PATTERNS:
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            return text[match.end() :].strip()
    return ""


# TXT FORMATTING
def format_document(text: str):
    bibliography = extract_bibliography(text)

    if bibliography:
        main_text = text.replace(bibliography, "").strip()
        has_bib = True
    else:
        main_text = text
        has_bib = False

    out = []
    out.append("# METADATA\n")
    out.append("Author: \n")
    out.append("Title: \n")
    out.append("Year: \n")
    out.append("Source_ID: \n")
    out.append("Source_Type: pdf\n")
    out.append("Pages: \n\n")

    out.append("# TEXT\n\n")
    out.append(main_text + "\n\n")

    out.append("# FIGURE\n\n")

    out.append("# BIBLIOGRAPHY\n\n")
    out.append(bibliography + "\n\n")

    return "".join(out), has_bib


# MAIN PIPELINE
def process_pdfs():
    ensure_dirs()

    processed = 0
    saved_txt = 0
    with_bib = 0
    no_bib = 0

    for pdf_path in PDF_INPUT_DIR.glob("*.pdf"):
        print("PDF FOUND:", pdf_path.name)
        processed += 1

        text = extract_text_auto(pdf_path)

        txt_name = f"{pdf_path.stem}.txt"
        txt_content, has_bib = format_document(text)

        raw_txt_path = TXT_RAW_DIR / txt_name
        copy_txt_path = TXT_COPY_DIR / txt_name

        raw_txt_path.write_text(txt_content, encoding="utf-8")
        shutil.copy(raw_txt_path, copy_txt_path)

        if has_bib:
            final_dir = TXT_WITH_BIB_DIR
            with_bib += 1
        else:
            final_dir = TXT_NO_BIB_DIR
            no_bib += 1

        shutil.copy(raw_txt_path, final_dir / txt_name)

        if raw_txt_path.exists() and copy_txt_path.exists():
            saved_txt += 1

    print("\n========== REPORT ==========")
    print(f"Processed PDFs: {processed}")
    print(f"TXT saved (raw + copy): {saved_txt}")
    print(f"With bibliography: {with_bib}")
    print(f"No bibliography: {no_bib}")
    print("================================")


if __name__ == "__main__":
    process_pdfs()
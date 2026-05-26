from io import BytesIO

from docx import Document
from pypdf import PdfReader


SUPPORTED_FILE_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def get_file_extension(filename: str) -> str:
    """
    Return the lowercase file extension from an uploaded filename.
    """
    if "." not in filename:
        return ""

    return "." + filename.rsplit(".", 1)[-1].lower()


def extract_text_from_txt_or_md(file_bytes: bytes) -> str:
    """
    Extract text from plain text or Markdown files.

    Uses UTF-8 first and falls back safely if the file contains unusual characters.
    """
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("utf-8", errors="replace")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from a PDF file using pypdf.

    Note:
    This works for text-based PDFs. Scanned image PDFs need OCR, which is not included here.
    """
    reader = PdfReader(BytesIO(file_bytes))
    page_texts = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            page_texts.append(f"\n\n[Page {page_number}]\n{text.strip()}")

    return "\n".join(page_texts).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from a DOCX file using python-docx.
    """
    document = Document(BytesIO(file_bytes))
    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs).strip()


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    """
    Extract text from supported upload types: TXT, MD, PDF, DOCX.
    """
    extension = get_file_extension(filename)

    if extension not in SUPPORTED_FILE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_FILE_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}")

    if extension in {".txt", ".md"}:
        return extract_text_from_txt_or_md(file_bytes)

    if extension == ".pdf":
        return extract_text_from_pdf(file_bytes)

    if extension == ".docx":
        return extract_text_from_docx(file_bytes)

    raise ValueError(f"Unsupported file type '{extension}'")

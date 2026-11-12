"""Turn an uploaded CV file into plain text. Everything happens on this machine."""
from pathlib import Path

ALLOWED = {".pdf", ".docx", ".txt"}


class ExtractError(Exception):
    pass


def text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # damaged or encrypted PDF
            raise ExtractError("This PDF could not be opened. Is it password-protected?") from exc
    elif ext == ".docx":
        import docx
        try:
            d = docx.Document(str(path))
        except Exception as exc:
            raise ExtractError("This Word file could not be opened.") from exc
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(parts)
    elif ext == ".txt":
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ExtractError("Only PDF, Word (.docx) and text files are supported.")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) < 150:
        raise ExtractError("Hardly any text could be read. If this is a scanned PDF, save it as a text-based PDF or Word file.")
    return text

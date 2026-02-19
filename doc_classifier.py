import os
import mimetypes
import pdfplumber

def classify_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                if text.strip():
                    return "PDF (text-based)"
                else:
                    return "PDF (scanned/image)"
        except Exception as e:
            return f"PDF (error reading): {str(e)}"

    elif ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
        return "Image"

    else:
        return f"Unknown or unsupported format: {mime_type or ext}"

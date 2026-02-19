import pdfplumber

def extract_text(file_path):
    """
    Extracts text from a text-based PDF or using OCR for scanned PDFs or images.   
    """
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text.strip()



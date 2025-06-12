import zipfile
from PyPDF2 import PdfReader
from typing import List, Dict
import io
import re

def extract_text_from_pdf(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_amounts_from_text(text: str) -> Dict[str, float]:
    """Extract currency amounts from invoice text"""
    amounts = {}
    # Match ₹ or ¥ followed by numbers
    inr_amounts = re.findall(r'[₹¥]\s*(\d+\.?\d*)', text)
    if inr_amounts:
        amounts['INR'] = float(inr_amounts[-1])  # Assuming last amount is total
    return amounts

def process_zip_invoices(zip_file) -> List[tuple]:
    """Process ZIP file containing multiple invoices"""
    invoices = []
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            if file_info.filename.lower().endswith('.pdf'):
                with zip_ref.open(file_info) as file:
                    content = file.read()
                    invoices.append((file_info.filename, io.BytesIO(content)))
    return invoices
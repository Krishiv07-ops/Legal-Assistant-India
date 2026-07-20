"""
ingest/extract_pdf.py
Extracts raw text from a downloaded Act PDF (e.g. from indiacode.nic.in).

Usage:
    python ingest/extract_pdf.py path/to/act.pdf > raw_text.txt

You get the PDF by manually downloading it from indiacode.nic.in in your
browser (Acts are public documents; this is not automated scraping).
"""

import sys
import pdfplumber


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_pdf.py path/to/act.pdf", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    text = extract_text(pdf_path)
    print(text)

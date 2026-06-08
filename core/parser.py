from typing import List, Dict, Any
import fitz  # PyMuPDF

def parse_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parses a PDF from its byte content.
    Extracts text from each page, using a smart OCR fallback via Tesseract if standard character count is < 50.
    
    Args:
        file_bytes: The raw bytes of the PDF file.
        filename: The name of the file (for metadata purposes).
        
    Returns:
        A list of dictionaries containing:
        - "text": The extracted/OCR'd text.
        - "filename": Name of the file.
        - "page_num": 1-based index of the page.
    """
    parsed_pages = []
    
    try:
        # Open PDF from memory bytes
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF file '{filename}': {str(e)}")
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        
        # Attempt standard digital text extraction
        try:
            text = page.get_text().strip()
        except Exception:
            text = ""
            
        # Smart Heuristic Fallback to OCR
        # If character count is less than 50, trigger Tesseract OCR via PyMuPDF
        if len(text) < 50:
            try:
                # Attempt to get text page using PyMuPDF's Tesseract OCR bindings
                textpage = page.get_textpage_ocr(language="eng")
                ocr_text = textpage.extractText().strip()
                
                # Check if OCR succeeded in retrieving more content
                if len(ocr_text) > len(text):
                    text = ocr_text
            except Exception as ocr_err:
                # Fallback to standard extraction if OCR is not available/configured
                # (e.g., Tesseract not installed on system PATH)
                pass
                
        # Include pages that yielded non-empty text
        if text:
            parsed_pages.append({
                "text": text,
                "filename": filename,
                "page_num": page_num
            })
            
    doc.close()
    return parsed_pages

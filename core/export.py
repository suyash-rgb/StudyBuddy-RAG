import tempfile
import markdown
import pymupdf
import os
import re
import zlib
import base64
import urllib.request
import logging
from core.session import get_messages

logger = logging.getLogger(__name__)

def encode_kroki(source: str) -> str:
    """Encodes diagram source code using zlib compression + URL-safe Base64 for Kroki API."""
    # Use raw deflate (wbits=-15) which suppresses zlib headers/footers as Kroki/PlantUML expect
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(source.encode('utf-8')) + compressor.flush()
    return base64.urlsafe_b64encode(compressed).decode('ascii')

def replace_diagrams_with_images_for_pdf(text: str, temp_files_list: list) -> str:
    """
    Finds diagram code blocks (Mermaid, Graphviz, PlantUML, D2) in markdown response text,
    fetches rendered SVG images from Kroki API, saves them locally, and replaces the
    code block with a local HTML <img> tag.
    """
    pattern = r"```(mermaid|graphviz|dot|plantuml|d2)\s*\n(.*?)\n```"
    
    def repl(match):
        lang = match.group(1).lower()
        code = match.group(2).strip()
        
        # Map dot to graphviz
        kroki_lang = "graphviz" if lang == "dot" else lang
        
        try:
            encoded = encode_kroki(code)
            # Use SVG format for vector scaling in the PDF document
            url = f"https://kroki.io/{kroki_lang}/svg/{encoded}"
            
            # Request image from Kroki
            req = urllib.request.Request(url, headers={'User-Agent': 'PdfInsight/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                img_data = response.read()
                
            # Write to a temp file
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
                f.write(img_data)
                temp_path = f.name
                
            temp_files_list.append(temp_path)
            abs_path = os.path.abspath(temp_path).replace(os.sep, "/")
            return f'<div style="text-align: center; margin: 15px 0;"><img src="file:///{abs_path}" style="max-width: 100%; height: auto; max-height: 400px; display: block; margin: 0 auto;"/></div>'
        except Exception as e:
            logger.error(f"Failed to render diagram to SVG image via Kroki for PDF: {e}")
            # Fallback: return standard fenced code block if rendering fails
            return match.group(0)
            
    return re.sub(pattern, repl, text, flags=re.DOTALL | re.IGNORECASE)

def export_conversation_to_pdf() -> bytes:
    """
    Extracts all assistant messages from the session state, converts them from Markdown
    to HTML (resolving inline diagrams and custom uploaded images), compiles the result,
    and generates a styled multipage PDF using PyMuPDF.
    Returns the raw bytes of the generated PDF.
    """
    messages = get_messages()
    assistant_msgs = []
    temp_files_to_clean = []
    
    for idx, msg in enumerate(messages):
        if msg["role"] != "assistant":
            continue
            
        content = msg["content"]
        
        # Replace inline diagram code blocks with local SVG files fetched from Kroki
        content_with_diagrams = replace_diagrams_with_images_for_pdf(content, temp_files_to_clean)
        
        # Convert markdown text to HTML
        html_msg = markdown.markdown(content_with_diagrams, extensions=['tables', 'fenced_code'])
        
        # Append any custom user annotations/images
        if msg.get("images"):
            html_msg += '<div style="margin-top: 15px; text-align: center;">'
            for img_path in msg["images"]:
                if os.path.exists(img_path):
                    abs_path = os.path.abspath(img_path).replace(os.sep, "/")
                    html_msg += f'<div style="margin-bottom: 10px;"><img src="file:///{abs_path}" style="max-width: 100%; height: auto; max-height: 350px; display: block; margin: 0 auto;"/></div>'
            html_msg += '</div>'
            
        assistant_msgs.append(html_msg)
        
    if not assistant_msgs:
        full_html = "<h2>No Conversation History</h2><p>There are no assistant responses to export yet.</p>"
    else:
        full_html = "<h1>Conversation Export</h1><br/>"
        for i, html_msg in enumerate(assistant_msgs):
            full_html += f"<h3>Response {i+1}</h3>{html_msg}<hr/>"
            
    # Premium styled HTML document layout
    styled_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Helvetica, sans-serif; padding: 15px; line-height: 1.6; color: #333333; }}
        h1 {{ color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 8px; margin-bottom: 20px; }}
        h2, h3 {{ color: #2c3e50; margin-top: 15px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; margin-bottom: 20px; font-size: 11px; }}
        th, td {{ border: 1px solid #cccccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f3f4f6; font-weight: bold; }}
        code {{ background-color: #f3f4f6; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
        pre {{ background-color: #f3f4f6; padding: 12px; border-radius: 6px; font-family: monospace; overflow-x: auto; font-size: 11px; }}
        hr {{ margin-top: 30px; margin-bottom: 30px; border: 0; border-top: 1px solid #e5e7eb; }}
        img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
    </style>
    </head>
    <body>
    {full_html}
    </body>
    </html>
    """

    # Write output to temporary PDF path
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_pdf_path = tmp.name
 
    try:
        MEDIABOX = pymupdf.paper_rect("letter")
        WHERE = MEDIABOX + (36, 36, -36, -36) # Margins
        
        story = pymupdf.Story(html=styled_html)
        writer = pymupdf.DocumentWriter(temp_pdf_path)
        
        more = 1
        while more:
            device = writer.begin_page(MEDIABOX)
            more, _ = story.place(WHERE)
            story.draw(device)
            writer.end_page()
            
        writer.close()
        
        # Read the compiled PDF bytes
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
    finally:
        # Clean up temporary SVG files
        for path in temp_files_to_clean:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.error(f"Failed to delete temporary SVG diagram file {path}: {e}")
                
        # Clean up temporary PDF file
        try:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except Exception as e:
            logger.error(f"Failed to delete temporary PDF export file {temp_pdf_path}: {e}")
            
    return pdf_bytes

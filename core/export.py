import tempfile
import markdown
import pymupdf
from core.session import get_messages

def export_conversation_to_pdf() -> bytes:
    """
    Extracts all assistant messages from the session state, converts them
    from Markdown to HTML, and generates a multipage PDF using PyMuPDF.
    Returns the raw bytes of the generated PDF.
    """
    messages = get_messages()
    assistant_msgs = [msg["content"] for msg in messages if msg["role"] == "assistant"]
    
    if not assistant_msgs:
        # If no messages, just return an empty pdf with a notice
        full_md = "## No Conversation History\nThere are no assistant responses to export yet."
    else:
        full_md = "# Conversation Export\n\n"
        for i, msg in enumerate(assistant_msgs):
            full_md += f"### Response {i+1}\n{msg}\n\n---\n\n"
            
    # Convert markdown to HTML. The 'tables' extension is needed because the LLM often generates tables.
    html_content = markdown.markdown(full_md, extensions=['tables', 'fenced_code'])
    
    # Optional styling to make the PDF look decent
    styled_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Helvetica, sans-serif; padding: 10px; line-height: 1.5; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 12px; }}
        th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f8f9fa; padding: 2px 4px; }}
        pre {{ background-color: #f8f9fa; padding: 10px; }}
        hr {{ margin-top: 20px; margin-bottom: 20px; border: 0; border-top: 1px solid #eee; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """

    # We will write to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_pdf_path = tmp.name

    # PyMuPDF PDF generation
    MEDIABOX = pymupdf.paper_rect("letter")
    # Margins (left, top, right, bottom)
    WHERE = MEDIABOX + (36, 36, -36, -36)
    
    story = pymupdf.Story(html=styled_html)
    writer = pymupdf.DocumentWriter(temp_pdf_path)
    
    more = 1
    while more:
        device = writer.begin_page(MEDIABOX)
        more, _ = story.place(WHERE)
        story.draw(device)
        writer.end_page()
        
    writer.close()
    
    # Read the bytes and return
    with open(temp_pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    return pdf_bytes

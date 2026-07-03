# StudyBuddy

StudyBuddy (formerly PdfInsight) is a lightweight, local-first academic study assistant that uses Retrieval-Augmented Generation (RAG) to help you understand your lecture notes, textbooks, slides, and images.

It supports comprehensive document parsing (including OCR for images) and generates highly accurate study responses with verifiable citations and dynamic inline diagram generation (Mermaid, Graphviz, PlantUML, D2).

## Prerequisites

- **Python 3.10+**
- **Tesseract OCR**: Required for extracting text from images (both standalone and embedded in PDFs/PPTs).
  - *Windows*: Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Ensure it is installed in `C:\Program Files\Tesseract-OCR` or add it to your system PATH.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/suyash-rgb/StudyBuddy-RAG.git
   cd StudyBuddy-RAG
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables:**
   - Create a file named `.env` in the root of the project.
   - Add your Groq API key:
     ```env
     GROQ_API_KEY=your_groq_api_key_here
     GROQ_MODEL=your_llm_model_name_here
     ```

## Startup Instructions

Run the Streamlit application from the root directory:

```bash
streamlit run app.py
```

The application will launch in your default web browser at `http://localhost:8501`.

## Features

- **Multi-Format Document Parsing:** PDF, DOCX, XLSX, CSV, TXT, JSONL, PPTX, and Images.
- **Local Vector Database:** Uses Qdrant and FastEmbed for privacy-focused, local semantic search.
- **Academic Guardrails:** LLM answers are strictly sourced from the document context with exact file/page citations.
- **Dynamic Diagrams:** Automatically detects if a query needs a diagram and generates Mermaid, Graphviz, PlantUML, or D2 diagrams seamlessly inline.
- **PDF Export:** Export your entire chat history, including diagrams, to a cleanly styled PDF document.

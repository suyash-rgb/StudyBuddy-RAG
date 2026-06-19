import os
import streamlit as st
import logging
from groq import Groq

logger = logging.getLogger(__name__)

@st.cache_resource
def get_groq_client() -> Groq:
    """
    Initializes and caches the Groq API client.
    Raises ValueError if GROQ_API_KEY is not found in the environment.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Please set it in your .env file.")
    return Groq(api_key=api_key)

def generate_study_response(query: str, context: str, diagram_tool: str | None = None) -> str:
    """
    Sends the user query along with retrieved reference context to Groq's LLM engine.
    Uses the model specified in the GROQ_MODEL env var (defaults to llama-3.3-70b-versatile).
    
    Args:
        query: The student's search/question string.
        context: Aggregated text blocks retrieved from Qdrant.
        diagram_tool: The selected diagramming language/tool to generate inline (e.g. 'Mermaid', 'Graphviz', 'PlantUML', 'D2').
        
    Returns:
        Structured response string in markdown format with citations.
    """
    try:
        client = get_groq_client()
    except ValueError as e:
        return f"⚠️ **Configuration Error:** {str(e)}"
        
    # Read model from environment or fall back to llama-3.3-70b-versatile
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    system_prompt = (
        "You are an elite academic tutor and researcher specializing in high-performance learning.\n"
        "Your task is to analyze the provided context blocks meticulously and draft thorough, "
        "scientifically rigorous, and highly accurate study answers for the user's query.\n\n"
        "Rigorous Constraints:\n"
        "1. Base your answer strictly on the provided context blocks. If the context does not contain "
        "sufficient information to fully answer the query, clearly state that the context is insufficient.\n"
        "2. Provide clear, direct in-text citations linking claims back to their source files and page numbers "
        "(e.g., [File: learning_guide.pdf, Page 4]). Do not generalize or make up citations.\n"
        "3. Maintain a professional, educational, and structured tone. Utilize Markdown (bolding, lists, "
        "tables, LaTeX formulas, or code blocks) to make the explanation easy to follow.\n"
        "4. Avoid speculative extrapolation. Ensure every claim can be traced to the context."
    )
    
    if diagram_tool:
        system_prompt += (
            f"\n\nDiagram Generation Instructions:\n"
            f"Since the user checked 'Add Diagrams' and the query requires a diagram, you MUST generate a diagram "
            f"using the tool: **{diagram_tool}**.\n"
            f"1. Generate the diagram code inside a fenced code block with the language identifier set to '{diagram_tool.lower()}'.\n"
            f"   For example:\n"
            f"   ```{diagram_tool.lower()}\n"
            f"   [Diagram code here]\n"
            f"   ```\n"
            f"2. IMPORTANT: Place this code block inline at the most relevant position within your response text (e.g., immediately "
            f"after the paragraph or section it explains/supports), rather than just putting it at the very end.\n"
            f"3. Make sure the code is syntax-valid for {diagram_tool}.\n"
            f"   - Mermaid: STRICT SYNTAX RULES: Use `graph TD` or `sequenceDiagram`. Node IDs (the part outside brackets) MUST be simple alphanumeric words WITHOUT spaces or quotes (e.g., `A`, `Node1`). NEVER use quotes, spaces, or special characters in the Node ID itself! You MUST wrap the text label of EVERY SINGLE node in double quotes (e.g., `A[\"Raw Data\"]` or `Node1[\"Linear Combination (z)\"]`). NEVER write a node label without double quotes if it contains spaces, parentheses, symbols, numbers, punctuation, or arrows. Do NOT use HTML tags inside node text.\n"
            f"   - Graphviz: Use clean DOT language syntax (e.g., `digraph G {{ ... }}`).\n"
            f"   - PlantUML: Use valid PlantUML syntax enclosed in `@startuml` and `@enduml`.\n"
            f"   - D2: Use valid D2 syntax (e.g., `x -> y`).\n"
            f"4. Integrate the diagram seamlessly into the flow of your explanation (e.g. 'The process follows this sequence: \\n\\n ```{diagram_tool.lower()}...\\n\\n Continuing explanation...')."
        )
        
    user_content = f"CONTEXT BLOCKS:\n{context}\n\nUSER QUERY:\n{query}"
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=model,
            temperature=0.1,  # Low temperature for factual precision
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error invoking Groq API:** {str(e)}"

def detect_diagram_scope(query: str) -> str:
    """
    Classifies whether the user's query requires or would significantly benefit from a diagram.
    Returns: 'Yes', 'No', or 'Ambiguous'.
    """
    query_clean = query.lower().strip()
    keywords = ["workflow", "process", "architecture", "flowchart", "diagram", "pipeline", "loop"]
    has_keyword = any(kw in query_clean for kw in keywords)
    
    try:
        client = get_groq_client()
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        prompt = (
            "Analyze the following academic search query and classify whether it has scope for or requires "
            "a visual diagram (like a flowchart, block/architecture diagram, UML diagram, or network graph) "
            "to explain the answer properly.\n\n"
            "Return EXACTLY one of the following words:\n"
            "- 'Yes': If the query is explicitly asking for a workflow, process, architecture, loop, network, "
            "hierarchy, sequence of events, or if explaining the answer inherently requires a visual flow.\n"
            "- 'No': If it is a simple factual recall, a simple math problem, code-only, or a direct textual definition.\n"
            "- 'Ambiguous': If the query might benefit from a diagram but is borderline or the user intent is not "
            "explicitly clear about needing a visual.\n\n"
            f"Query: \"{query}\"\n"
            "Classification (output only 'Yes', 'No', or 'Ambiguous'):"
        )
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
            max_tokens=10
        )
        
        res = completion.choices[0].message.content.strip().lower()
        if "yes" in res:
            return "Yes"
        elif "no" in res:
            # Fallback heuristic: if LLM says No but keywords match, mark as Ambiguous
            if has_keyword:
                return "Ambiguous"
            return "No"
        else:
            return "Ambiguous"
            
    except Exception as e:
        logger.error(f"Failed to detect diagram scope with LLM: {e}")
        # Heuristic fallback
        return "Yes" if has_keyword else "No"

def select_diagram_tool(query: str) -> str:
    """
    Selects the most appropriate diagramming tool/library for the query.
    Returns one of: 'Mermaid', 'Graphviz', 'PlantUML', or 'D2'.
    """
    try:
        client = get_groq_client()
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        prompt = (
            "Analyze the following user query and choose the most suitable diagramming tool for the explanation.\n"
            "Choose exactly one of the following: 'Mermaid', 'Graphviz', 'PlantUML', or 'D2'.\n\n"
            "Classification Rules:\n"
            "1. Choose 'Mermaid' for: standard flowcharts, sequential loops, simple sequence diagrams, and state transitions.\n"
            "2. Choose 'Graphviz' for: network graphs, complex nodes and edges with custom shapes, math graphs, and dense trees.\n"
            "3. Choose 'PlantUML' for: software UML, class diagrams, detailed sequence diagrams, and database schemas.\n"
            "4. Choose 'D2' for: cloud or systems architecture, org charts, directory trees, and polished high-level architecture designs.\n\n"
            f"Query: \"{query}\"\n"
            "Selection (output ONLY the chosen tool name):"
        )
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
            max_tokens=10
        )
        
        res = completion.choices[0].message.content.strip().lower()
        if "mermaid" in res:
            return "Mermaid"
        elif "graphviz" in res or "dot" in res:
            return "Graphviz"
        elif "plantuml" in res:
            return "PlantUML"
        elif "d2" in res:
            return "D2"
        else:
            return "Mermaid"  # Fallback
            
    except Exception as e:
        logger.error(f"Failed to select diagram tool with LLM: {e}")
        return "Mermaid"  # Fallback

import json
import re

VOCAB_FILE = os.path.join("qdrant_db", "vocabulary.json")

# Static dictionary of common English words and tech/RAG terms
STATIC_VOCAB = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", 
    "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", 
    "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", 
    "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", 
    "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", 
    "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", 
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us", "is", "are", "was", "were",
    "hello", "hi", "yes", "no", "help", "please", "thanks", "thank",
    "lstm", "rag", "cnn", "rnn", "bert", "gpt", "llm", "model", "nlp", "api", "json", "pdf", "docx", "pptx", 
    "excel", "csv", "image", "figure", "diagram", "page", "show", "explain", "summary", "document", "system", 
    "vector", "embedding", "database", "qdrant", "python", "code", "streamlit", "error", "failed", "run", "test", 
    "file", "data", "query", "search", "context", "math", "find", "where", "why", "describe", "meaning", "definition"
}

def update_document_vocabulary(texts: list[str]):
    """
    Parses words from the indexed document texts, merges them with any existing vocabulary,
    and saves them to a local vocabulary file for zero-false-positive intent checks.
    """
    try:
        existing_vocab = set()
        if os.path.exists(VOCAB_FILE):
            with open(VOCAB_FILE, "r", encoding="utf-8") as f:
                existing_vocab = set(json.load(f))
        
        new_words = set()
        for text in texts:
            # Find all words of length 2-20 containing alphabetic chars or apostrophes
            found = re.findall(r"\b[a-zA-Z']{2,20}\b", text.lower())
            new_words.update(found)
            
        merged_vocab = existing_vocab.union(new_words)
        os.makedirs(os.path.dirname(VOCAB_FILE), exist_ok=True)
        with open(VOCAB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(merged_vocab), f)
            
        logger.info(f"Updated vocabulary file with {len(new_words)} new words. Total vocab size: {len(merged_vocab)}.")
    except Exception as e:
        logger.error(f"Failed to update document vocabulary: {e}")

def clear_document_vocabulary():
    """Deletes the vocabulary file when the database is cleared."""
    try:
        if os.path.exists(VOCAB_FILE):
            os.remove(VOCAB_FILE)
            logger.info("Cleared document vocabulary file.")
    except Exception as e:
        logger.error(f"Failed to clear document vocabulary: {e}")

def _get_valid_bigrams(vocab: set) -> set:
    """Generates all valid character bigrams from a vocabulary set."""
    bigrams = set()
    for word in vocab:
        word = word.replace("'", "")
        for i in range(len(word) - 1):
            bigrams.add(word[i:i+2])
    return bigrams

def analyze_query_intent(query: str) -> dict:
    """
    Fast, pure-Python hybrid algorithm to classify the query intent BEFORE hitting the heavy RAG pipeline.
    Determines if the query is bogus/gibberish, and whether the user is asking for an image.
    Uses zero LLM API calls.
    """
    query_clean = query.lower().strip()
    
    parsed_intent = {
        "is_bogus": False,
        "is_image_query": False,
        "page_num": None
    }
    
    # --- 1. IMAGE ROUTING INTENT ---
    # Look for explicit commands to show/display/view/see/get
    command_match = re.search(
        r"\b(show|view|display|see|get|extract|fetch|render|output|draw|open|find)\b.*?\b(image|figure|diagram|picture|photo|illustration|chart|plot|graph)s?\b",
        query_clean
    )
    
    # Look for "show page X images" or "images on page X" or "page X figures"
    page_match = re.search(
        r"\b(image|figure|diagram|picture|photo|illustration|chart|plot|graph)s?\b.*?\b(page|pg\.?)\s+(\d+|last)\b",
        query_clean
    )
    page_match_alt = re.search(
        r"\b(page|pg\.?)\s+(\d+|last)\b.*?\b(image|figure|diagram|picture|photo|illustration|chart|plot|graph)s?\b",
        query_clean
    )
    
    # Check for question/explanation intent
    question_words = r"\b(what|why|how|explain|describe|summarize|tell|who|where|meaning|definition)\b"
    has_question = bool(re.search(question_words, query_clean))
    
    if (command_match or page_match or page_match_alt) and not (has_question and not command_match):
        parsed_intent["is_image_query"] = True
        
        pg_match = re.search(r"\b(page|pg\.?)\s+(\d+|last)\b|\b(last)\s+(page|pg\.?)\b", query_clean)
        if pg_match:
            val = pg_match.group(2) or pg_match.group(3)
            parsed_intent["page_num"] = "last" if val == "last" else int(val)
        else:
            num_match = re.search(r"\b(\d+)\b", query_clean)
            if num_match:
                parsed_intent["page_num"] = int(num_match.group(1))
                
    # --- 2. GIBBERISH / SPAM DETECTION ---
    # Load dynamic vocabulary if exists
    dynamic_vocab = set()
    if os.path.exists(VOCAB_FILE):
        try:
            with open(VOCAB_FILE, "r", encoding="utf-8") as f:
                dynamic_vocab = set(json.load(f))
        except Exception:
            pass
            
    combined_vocab = STATIC_VOCAB.union(dynamic_vocab)
    valid_bigrams = _get_valid_bigrams(combined_vocab)
    
    # Check if query contains math/code symbols. If so, it's not bogus.
    if re.search(r"[=\+\-\*\/\^<>\[\]\{\}\(\)]", query):
        return parsed_intent
        
    words = re.findall(r"\b[a-z']+\b", query_clean)
    if not words:
        # If no words but contains symbols (and wasn't caught by math check), it's bogus
        if re.search(r"[^\w\s]", query_clean):
            parsed_intent["is_bogus"] = True
        return parsed_intent
        
    bogus_count = 0
    for w in words:
        if w in combined_vocab:
            continue
        if len(w) <= 3:
            continue
            
        is_bogus_word = False
        
        # 1. Repetitive characters (3+ identical)
        if re.search(r"(.)\1\1", w):
            is_bogus_word = True
            
        # 2. Consecutive consonants (5+) (treating y as a vowel to be safe)
        elif re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", w):
            is_bogus_word = True
            
        # 3. Vowel starvation (length >= 5 and 0 vowels)
        elif len(w) >= 5 and not re.search(r"[aeiouy]", w):
            is_bogus_word = True
            
        # 4. Keyboard walks
        elif any(walk in w or walk[::-1] in w for walk in ["asdf", "qwer", "zxcv", "sdfg", "wert", "xcvb", "dfgh", "erty", "cvbn", "fghj", "rtyu", "vbnm", "ghjk", "tyui", "hjkl", "yuio", "uiop"]):
            is_bogus_word = True
            
        # 5. Language Bigram Probability Check
        else:
            w_clean = w.replace("'", "")
            if len(w_clean) >= 4:
                w_bigrams = [w_clean[i:i+2] for i in range(len(w_clean) - 1)]
                unseen = sum(1 for bg in w_bigrams if bg not in valid_bigrams)
                if unseen / len(w_bigrams) >= 0.5:
                    is_bogus_word = True
                    
        if is_bogus_word:
            bogus_count += 1
            
    if (bogus_count / len(words)) >= 0.5 or (bogus_count > 0 and len(words) <= 2):
        parsed_intent["is_bogus"] = True
        
    return parsed_intent

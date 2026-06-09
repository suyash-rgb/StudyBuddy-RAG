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

def generate_study_response(query: str, context: str) -> str:
    """
    Sends the user query along with retrieved reference context to Groq's LLM engine.
    Uses the model specified in the GROQ_MODEL env var (defaults to llama-3.3-70b-versatile).
    
    Args:
        query: The student's search/question string.
        context: Aggregated text blocks retrieved from Qdrant.
        
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

import json

def classify_image_intent(query: str) -> dict:
    """
    Uses the Groq LLM to quickly determine if the user is asking to see images, 
    and if they specified a page number.
    Returns a dict: {"is_image_query": bool, "page_num": int | None}
    """
    try:
        client = get_groq_client()
    except ValueError:
        return {"is_image_query": False, "page_num": None}
        
    system_prompt = (
        "You are an intent classification engine. Analyze the user's query and determine "
        "if they are asking to view, see, display, or show images/figures from a document. "
        "If they specify a specific numeric page number, extract it as an integer. If they ask for the last page, return the exact string 'last'. For any other non-specific page requests (e.g., 'all pages', 'this document'), return null for page_num. "
        "You must respond ONLY with a valid JSON object matching this exact schema: "
        '{"is_image_query": true or false, "page_num": int or "last" or null}'
    )
    
    try:
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model=model,
            temperature=0,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        intent = json.loads(content)
        
        # Ensure page_num is either an integer, "last", or None
        if intent.get("page_num") is not None and intent.get("page_num") != "last":
            try:
                intent["page_num"] = int(intent["page_num"])
            except (ValueError, TypeError):
                intent["page_num"] = None
                
        return intent
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {"is_image_query": False, "page_num": None}

import os
import json
import logging
from core.llm_engine import analyze_query_intent, update_document_vocabulary, VOCAB_FILE

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def run_tests():
    # Setup test vocabulary
    test_docs = [
        "This is a test document explaining backpropagation and eigenvalues in a neural network.",
        "The architecture diagram on page 5 shows the full system."
    ]
    update_document_vocabulary(test_docs)
    
    test_cases = [
        # Gibberish tests
        ("dhgfhsb", {"is_bogus": True, "is_image_query": False, "page_num": None}),
        ("asdfgh", {"is_bogus": True, "is_image_query": False, "page_num": None}),
        ("aaaa", {"is_bogus": True, "is_image_query": False, "page_num": None}),
        ("hello asdf", {"is_bogus": True, "is_image_query": False, "page_num": None}),
        
        # Tech acronyms
        ("LSTM", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        ("RAG", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        ("CNN", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        
        # Equations/Code
        ("y = mx + c", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        ("def foo():", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        
        # Domain terms from doc
        ("backpropagation", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        ("eigenvalues", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        
        # Image queries
        ("show me the figure on page 3", {"is_bogus": False, "is_image_query": True, "page_num": 3}),
        ("view the diagram", {"is_bogus": False, "is_image_query": True, "page_num": None}),
        ("display the last page figure", {"is_bogus": False, "is_image_query": True, "page_num": "last"}),
        ("image on page 5", {"is_bogus": False, "is_image_query": True, "page_num": 5}),
        
        # Text questions that mention images
        ("explain what figure 3 is showing", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        ("what is in the diagram on page 5?", {"is_bogus": False, "is_image_query": False, "page_num": None}),
        
        # Combined request
        ("show me the diagram on page 5 and explain what it is", {"is_bogus": False, "is_image_query": True, "page_num": 5}),
    ]
    
    passed = 0
    for query, expected in test_cases:
        result = analyze_query_intent(query)
        # Check against expected
        if result == expected:
            passed += 1
            print(f"✅ PASS: '{query}'")
        else:
            print(f"❌ FAIL: '{query}'")
            print(f"   Expected: {expected}")
            print(f"   Got:      {result}")
            
    print(f"\n--- Results: {passed}/{len(test_cases)} Passed ---")

if __name__ == "__main__":
    run_tests()
    
    # Cleanup test vocab
    if os.path.exists(VOCAB_FILE):
        os.remove(VOCAB_FILE)

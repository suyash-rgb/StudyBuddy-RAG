import re
import zlib
import base64
import string
import streamlit as st
import streamlit.components.v1 as components

def plantuml_encode(plantuml_text: str) -> str:
    """Compress and encode PlantUML text for a PlantUML server."""
    plantuml_alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
    base64_alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
    
    trans_table = bytes.maketrans(base64_alphabet.encode('utf-8'), plantuml_alphabet.encode('utf-8'))
    
    zlibbed_str = zlib.compress(plantuml_text.encode('utf-8'))
    compressed_string = zlibbed_str[2:-4]
    return base64.b64encode(compressed_string).translate(trans_table).decode('utf-8')

def render_mermaid(code: str):
    """Renders Mermaid diagram using the remote Mermaid Ink API."""
    import json
    import urllib.request
    from core.export import sanitize_mermaid_code
    try:
        code = sanitize_mermaid_code(code)
        payload = json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").replace("=", "")
        url = f"https://mermaid.ink/img/{encoded}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            img_data = response.read()
            
        b64 = base64.b64encode(img_data).decode('utf-8')
        st.markdown(f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/jpeg;base64,{b64}" style="max-width: 100%; height: auto; max-height: 500px; display: block; margin: 0 auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Diagram could not be rendered (syntax error). Falling back to code:")
        st.code(code, language="mermaid")

def render_graphviz(code: str):
    """Renders DOT Graphviz diagram using Streamlit native widget."""
    try:
        st.graphviz_chart(code, use_container_width=False)
    except Exception as e:
        st.error(f"Error rendering Graphviz diagram: {e}")
        st.code(code, language="dot")

def render_plantuml(code: str):
    """Renders PlantUML diagram using the remote PlantUML image API."""
    import urllib.request
    try:
        encoded = plantuml_encode(code)
        url = f"https://www.plantuml.com/plantuml/png/{encoded}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            img_data = response.read()
            
        b64 = base64.b64encode(img_data).decode('utf-8')
        st.markdown(f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/png;base64,{b64}" style="max-width: 100%; height: auto; max-height: 500px; display: block; margin: 0 auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Diagram could not be rendered (syntax error). Falling back to code:")
        st.code(code, language="plantuml")

def render_d2(code: str):
    """Renders D2 diagram in a Streamlit HTML component using WASM via CDN."""
    js_safe_code = code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    html_content = f"""
    <div id="d2-container" style="width: 100%; height: 100%;">Rendering D2 Diagram...</div>
    <script type="module">
        import {{ D2 }} from 'https://esm.sh/@terrastruct/d2';
        
        async function init() {{
            try {{
                const d2 = new D2();
                const code = `{js_safe_code}`;
                const result = await d2.compile(code);
                const svg = await d2.render(result.diagram, result.renderOptions);
                const container = document.getElementById('d2-container');
                container.innerHTML = svg;
            }} catch (err) {{
                document.getElementById('d2-container').innerHTML = '<pre style="color:red;">Error: ' + err.message + '</pre>';
            }}
        }}
        init();
    </script>
    """
    components.html(html_content, height=450, scrolling=True)

def render_inline_diagram(lang: str, code: str):
    """Routes the diagram rendering to the appropriate tool renderer."""
    lang = lang.lower().strip()
    if lang == "mermaid":
        render_mermaid(code)
    elif lang in ("graphviz", "dot"):
        render_graphviz(code)
    elif lang == "plantuml":
        render_plantuml(code)
    elif lang == "d2":
        render_d2(code)

def display_response_with_diagrams(text: str):
    """
     Splits the Markdown response and renders sections sequentially,
     replacing diagram fenced blocks with their actual rendered component widgets.
     """
    pattern = r"```(mermaid|graphviz|dot|plantuml|d2)\b[^\n]*\r?\n(.*?)\r?\n\s*```"
    parts = re.split(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    
    i = 0
    while i < len(parts):
        normal_text = parts[i]
        if normal_text.strip():
            st.markdown(normal_text, unsafe_allow_html=True)
            
        if i + 2 < len(parts):
            lang = parts[i+1]
            code = parts[i+2]
            render_inline_diagram(lang, code)
            i += 3
        else:
            i += 1

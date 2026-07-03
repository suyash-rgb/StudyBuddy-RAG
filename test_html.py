import core.export
import pymupdf

message = {
    "role": "assistant",
    "content": '''Visual Overview of the SDLC

The following Mermaid diagram illustrates the sequential flow of the SDLC stages and highlights the key deliverables at each step.

```mermaid
graph TD
A[Requirement Gathering] --> B[Requirement Analysis]
B --> C[Feasibility Study]
C --> D[Documentation SRS]
D --> E[Design]
E --> F[Coding]
F --> G[Testing]
G --> H[Deployment]
```

And high team maturity.
'''
}

core.export.get_messages = lambda: [message]

html_list = []
orig_story = pymupdf.Story
class MockStory:
    def __init__(self, html, *args, **kwargs):
        html_list.append(html)
        self.orig = orig_story(html=html, *args, **kwargs)
    def place(self, *args, **kwargs): return self.orig.place(*args, **kwargs)
    def draw(self, *args, **kwargs): return self.orig.draw(*args, **kwargs)

core.export.pymupdf.Story = MockStory

try:
    core.export.export_conversation_to_pdf()
except Exception as e:
    print("Error:", e)

if html_list:
    open('test_sdlc.html', 'w', encoding='utf-8').write(html_list[0])
    print("Saved HTML!")
else:
    print("No HTML generated!")

import core.export
import tempfile
import os

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

# mock get_messages
core.export.get_messages = lambda: [message]

pdf_bytes = core.export.export_conversation_to_pdf()
with open("test_sdlc.pdf", "wb") as f:
    f.write(pdf_bytes)
print("Saved to test_sdlc.pdf")

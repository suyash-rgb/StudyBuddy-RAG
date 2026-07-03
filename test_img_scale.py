import pymupdf
import os

img_path = 'temp_exports/tmpphq280a3.png'

html_content = f'''
<h1>Test Styles</h1>

<h2>1. max-width: 100%; max-height: 400px;</h2>
<img src="{img_path}" style="max-width: 100%; max-height: 400px;" />

<h2>2. width="100%"</h2>
<img src="{img_path}" width="100%" />

<h2>3. width="80%"</h2>
<img src="{img_path}" width="80%" />

<h2>4. No attributes</h2>
<img src="{img_path}" />
'''

MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('test_styles.pdf')

more = 1
while more:
    device = writer.begin_page(MEDIABOX)
    more, _ = story.place(WHERE)
    story.draw(device)
    writer.end_page()

writer.close()
print("Saved to test_styles.pdf")

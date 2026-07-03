import pymupdf
import os

img_path = 'temp_exports/tmpphq280a3.png'

html_content = f'''
<h1>Test Styles</h1>

<h2>1. style="width: 100%"</h2>
<img src="{img_path}" style="width: 100%;" />

<h2>2. width="400"</h2>
<img src="{img_path}" width="400" />
'''

MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('test_styles_2.pdf')

more = 1
while more:
    device = writer.begin_page(MEDIABOX)
    more, _ = story.place(WHERE)
    story.draw(device)
    writer.end_page()

writer.close()

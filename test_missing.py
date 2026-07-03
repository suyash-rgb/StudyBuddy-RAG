import pymupdf
import os

html_content = '<img src="does_not_exist.png" width="300" height="150" style="background-color: #f3f4f6;" />'
MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('test_missing.pdf')
device = writer.begin_page(MEDIABOX)
story.place(WHERE)
story.draw(device)
writer.end_page()
writer.close()
print("Saved to test_missing.pdf")

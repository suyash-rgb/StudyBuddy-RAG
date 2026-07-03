import pymupdf
doc = pymupdf.open('test_output.pdf')
images = doc[0].get_images()
print('Images found:', len(images))
if len(images) > 0:
    print('Image dimensions:', images[0][2], 'x', images[0][3])

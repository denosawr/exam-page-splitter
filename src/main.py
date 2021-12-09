import sys
from pathlib import Path
from pprint import pprint

import PyPDF2

import question_splitter

# convert to command-line (click) later
file = sys.argv[1]
path = Path(file)

results = question_splitter.split_question(file)

pprint(results)

import pdf_splitter

src_f = open(file, "rb")
input_PDF = PyPDF2.PdfFileReader(file)

parent = path.parent
folder = parent / path.stem
folder.mkdir(exist_ok=True)

for question, pages in results.items():
    output = PyPDF2.PdfFileWriter()
    for page_data in pages:
        print(question, page_data)
        p: PyPDF2.pdf.PageObject = input_PDF.getPage(page_data.page)
        new_page = pdf_splitter.extract_viewport(p, page_data.viewport)

        output.addPage(new_page)
    with open(folder / (str(question) + ".pdf"), "wb") as f:
        output.write(f)

src_f.close()

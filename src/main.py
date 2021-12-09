import sys
from pprint import pprint

import PyPDF2

import question_splitter

# convert to command-line (click) later
file = sys.argv[1]
results = question_splitter.split_question(file)

pprint(results)

import pdf_splitter

src_f = open(file, "rb")
output = PyPDF2.PdfFileWriter()
for question, pages in results.items():
    for page_data in pages:
        print(question, page_data)
        input_PDF = PyPDF2.PdfFileReader(file)
        p: PyPDF2.pdf.PageObject = input_PDF.getPage(page_data.page)
        new_page = pdf_splitter.extract_viewport(p, page_data.viewport)

        output.addPage(new_page)
src_f.close()

with open("tests/output.pdf", "wb") as f:
    output.write(f)

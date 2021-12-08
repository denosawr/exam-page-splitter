# import pdfrw
import sys

from file_parser import PDFTextFinder


# convert to command-line (click) later
file = sys.argv[1]

import re

# for page in pages:
#     print(page)
#     sys.exit()

SEARCH_FOR_QUESTION_REGEX = re.compile(r"Question (\d)", re.IGNORECASE)


print("x1  y1  x2  y2   text")
from pprint import pprint

f = PDFTextFinder(file)
pprint(f.find_matches(SEARCH_FOR_QUESTION_REGEX))
f.close()

import sys
from pprint import pprint

import question_splitter

# convert to command-line (click) later
file = sys.argv[1]
pprint(question_splitter.split_question(file))

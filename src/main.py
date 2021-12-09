import sys
from pprint import pprint

import splitter

# convert to command-line (click) later
file = sys.argv[1]
pprint(splitter.split_question(file))

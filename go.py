#!/usr/bin/python

import sys
from PLD_Builder.get_br import *

for f in sys.argv[1:]:
  get_build_requires(f, [], [])

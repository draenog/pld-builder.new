#!/usr/bin/python

import sys
from PLD_Builder.squeue import *
from PLD_Builder.request import *
from PLD_Builder.gpg import *

q = Src_Queue("src-queue")
#q.read()
(em, b) = gpg.verify_sig(open("req.txt"))
q.add(parse_request(b))
q.write()

for r in q.value():
  r.dump()

#!/usr/bin/python

import sys
import time
from PLD_Builder.bqueue import *
from PLD_Builder.request import *
from PLD_Builder.gpg import *

q = B_Queue("src-queue")
q.lock(0)
q.read()
(em, b) = gpg.verify_sig(open("req.txt"))
q.add(parse_request(b))
q.write()
q.unlock()

for r in q.value():
  r.dump()

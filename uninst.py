#!/usr/bin/python

import sys
from PLD_Builder.deps import *

req = compute_deps()

def main():
  req = compute_deps()
  m = {}
  def close(p):
    if m.has_key(p):
      return
    m[p] = 1
    for x in req[p]:
      close(x)
  close("rpm-build")
  for x in m.keys():
    print x

main()

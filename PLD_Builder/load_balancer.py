import string
import os
import time

import path
import log
import status
import lock
import util
from config import config, init_conf

# return list of binary builders in fair-queue order
# it is determined based upon spool/got_lock file, which is also
# updated to be short
def builders_order():
  bs = {}
  bl = []
  for b in config.builders:
    bs[b] = 0
    bl.append(b)
    
  lck = lock.lock("got-lock")
  f = open(path.got_lock_file, "r+")
  line_no = 0
  
  for l in f.xreadlines():
    line_no += 1
    b = string.strip(l)
    if bs.has_key(b):
      bs[b] = line_no
    else:
      log.alert("found strange lock in got-lock: %s" % b)

  bl.sort(lambda (b1, b2): cmp(bs[b1], bs[b2]))

  f.seek(0)
  f.truncate(0)
  for l in bl: f.write(l + "\n")
  f.close()
  lck.close()

  return bl

def run_rpm_builder(b):
  prog = path.root_dir + "binary_builder/rpm-builder.sh"
  os.spawnl(os.P_NOWAIT, prog, prog, b)

def main():
  init_conf("")
  for b in builders_order():
    run_rpm_builder(b)
    # give builder some time to aquire lock
    time.sleep(1)
  # wait for children to die out
  try:
    while 1: os.wait()
  except:
    pass

util.wrap(main)

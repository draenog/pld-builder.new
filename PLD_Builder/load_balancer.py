import string
import os
import time

import path
import sys
import log
import status
import lock
import wrap

import rpm_builder

from config import config, init_conf

# return list of binary builders in fair-queue order
# it is determined based upon spool/got_lock file, which is also
# updated to be short
def builders_order():
  bs = {}
  bl = []
  for b in config.binary_builders:
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

  def mycmp(b1, b2):
    return cmp(bs[b1], bs[b2])
    
  bl.sort(mycmp)

  f.seek(0)
  f.truncate(0)
  for l in bl: f.write(l + "\n")
  f.close()
  lck.close()

  return bl

def run_rpm_builder(b):
  if os.fork() == 0:
    return
  else:
    rpm_builder.main_for(b)
    sys.exit(0)

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

if __name__ == '__main__':
  wrap.wrap(main)

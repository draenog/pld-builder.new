import email
import string
import time
import os
import StringIO
import sys

import gpg
import request
import log
import path
from acl import acl
from lock import lock
from bqueue import B_Queue

import chroot # needs to be fixed

def pick_request(q):
  def mycmp(r1, r2):
    if r1.kind != 'group' or r2.kind != 'group':
      raise "non-group requests"
    pri_diff = cmp(r1.priority, r2.priority)
    if pri_diff == 0:
      return cmp(r1.time, r2.time)
    else:
      return pri_diff
  q.batches.sort(mycmp)
  ret = q.batches[0]
  q.batches = q.batches[1:]
  return ret


def handle_request(r):
  def build_srpm(b):
    builder_opts = "-nu --clean"
    f = chroot.popen("cd rpm/SPECS; ./builder %s -bs %s -r %s %s 2>&1" % \
                 (build_opts, b.bconds_string(), b.branch, b.spec))
    log = StringIO.StringIO()
    log.write(f.read())
    res = f.close()
    log.seek(0)
    files = []
    for l in log.readlines():
      re.search(r"^Wrote: (/home.*\.rpm)")
      #finish me


  user = acl.user(r.requester)
  log.notice("started processing %s" % r.id)
  os.mkdir(path.srpms_dir + r.id)
  
def main():
  lock("building-srpm")
  q = B_Queue(path.queue_file)
  if not q.lock(1): return
  q.read()
  if q.batches == []: return
  r = pick_request(q)
  q.write()
  q.unlock()
  handle_request(r)

main()

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

import chroot

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

def collect_files(log):
  f = open(log)
  rx = re.compile(r"^Wrote: (/home.*\.rpm)$")
  files = []
  for l in f.xreadlines():
    m = rx.search(l)
    if m:
      files.append(m.group(1))
  return files

def append_to(log, msg)
  f = open(log, "a")
  f.write("%s\n" % msg)
  f.close()
  
def handle_request(r):
  def build_srpm(b):
    b.src_rpm = ""
    builder_opts = "-nu --clean --nodeps"
    cmd = "cd rpm/SPECS; ./builder %s -bs %s -r %s %s 2>&1" % \
                 (build_opts, b.bconds_string(), b.branch, b.spec)
    res = chroot.run(cmd, logfile = log)
    files = collect_files(log)
    if len(files) > 0:
      if len(files) > 1:
        append_to(log, "error: More then one file produced."
        res = 1
      b.src_rpm = files[len(files) - 1]
      all_files.extend(files)
    else:
      append_to(log, "error: No files produced."
      res = 1
    return res

  tmp = spool_dir + r.id
  mkdir(tmp)
  log = tmp + "log"
  user = acl.user(r.requester)
  log.notice("started processing %s" % r.id)
  all_files = []
  for batch in r.batches:
    if build_srpm(batch):
      # clean up
      chroot.run("rm -f %s" % string.join(all_files))
      user.notify_about_failure()
      break
  if oops:
  else:
    os.mkdir(path.srpms_dir + r.id)
    for f in files:
      # export files from chroot
      rpm = 
      local = path.srpms_dir + r.id + "/" + os.path.basename(f)
      chroot.run("cat %s; rm -f %s" % (f, f), logfile = local)
  
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

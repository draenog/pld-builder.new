import email
import string
import time
import os
import os.path
import StringIO
import sys
import re
import atexit

import gpg
import request
import log
import path
import util
import chroot
import buildlogs
import ftp
import status

from acl import acl
from lock import lock
from bqueue import B_Queue
from config import config, init_conf

def pick_request(q):
  def mycmp(r1, r2):
    if r1.kind != 'group' or r2.kind != 'group':
      raise "non-group requests"
    pri_diff = cmp(r1.priority, r2.priority)
    if pri_diff == 0:
      return cmp(r1.time, r2.time)
    else:
      return pri_diff
  q.requests.sort(mycmp)
  ret = q.requests[0]
  q.requests = q.requests[1:]
  return ret
  
def send_files(r):
  os.mkdir(path.srpms_dir + r.id)
  os.chmod(path.srpms_dir + r.id, 0755)
  for batch in r.batches:
    if batch.build_failed: continue
    # export files from chroot
    local = path.srpms_dir + r.id + "/" + batch.src_rpm
    f = batch.src_rpm_file
    chroot.run("cat %s; rm -f %s" % (f, f), logfile = local)
    os.chmod(local, 0644)
    ftp.add(local)

def store_binary_request(r):
  new_b = []
  for b in r.batches:
    if not b.build_failed: new_b.append(b)
  if new_b == []:
    return
  r.batches = new_b
  # store new queue and max_req_no for binary builders
  cnt_f = open(path.max_req_no_file, "r+")
  num = int(string.strip(cnt_f.read())) + 1
  r.no = num
  q = B_Queue(path.req_queue_file)
  q.lock(0)
  q.read()
  q.add(r)
  q.write()
  q.dump(open(path.queue_stats_file, "w"))
  os.chmod(path.queue_stats_file, 0644)
  q.write_signed(path.req_queue_signed_file)
  os.chmod(path.req_queue_signed_file, 0644)
  q.unlock()
  cnt_f.seek(0)
  cnt_f.write("%d\n" % num)
  cnt_f.close()
  os.chmod(path.max_req_no_file, 0644)
  
def build_srpm(r, b):
  status.push("building %s" % b.spec)
  b.src_rpm = ""
  builder_opts = "-nu --clean --nodeps"
  cmd = "cd rpm/SPECS; ./builder %s -bs %s -r %s %s 2>&1" % \
               (builder_opts, b.bconds_string(), b.branch, b.spec)
  util.append_to(b.logfile, "request from: %s" % r.requester)
  util.append_to(b.logfile, "started at: %s" % time.asctime())
  util.append_to(b.logfile, "building SRPM using: %s\n" % cmd)
  res = chroot.run(cmd, logfile = b.logfile)
  util.append_to(b.logfile, "exit status %d" % res)
  files = util.collect_files(b.logfile)
  if len(files) > 0:
    if len(files) > 1:
      util.append_to(b.logfile, "error: More then one file produced: %s" % files)
      res = 1
    last = files[len(files) - 1]
    b.src_rpm_file = last
    b.src_rpm = os.path.basename(last)
    r.chroot_files.extend(files)
  else:
    util.append_to(b.logfile, "error: No files produced.")
    res = 1
  buildlogs.add(logfile = b.logfile, failed = res)
  status.pop()
  return res

def handle_request(r):
  r.build_all(build_srpm)
  send_files(r)
  r.clean_files()
  r.send_report()
  store_binary_request(r)
  buildlogs.flush()
  ftp.flush()

def main():
  init_conf("src")
  if lock("building-srpm", non_block = 1) == None:
    return
  status.push("srpm: processing queue")
  q = B_Queue(path.queue_file)
  if not q.lock(1): return
  q.read()
  if q.requests == []: return
  r = pick_request(q)
  q.write()
  q.unlock()
  status.pop()
  status.push("srpm: handling request from %s" % r.requester)
  handle_request(r)
  status.pop()

util.wrap(main)

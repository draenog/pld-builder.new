import glob
import re
import string
import os
import time
import shutil

from acl import acl
from config import config, init_conf
import mailer
import path
import util
import log
import status

retries_times = [5 * 60, 15 * 60, 60 * 60, 2 * 60 * 60, 5 * 60 * 60]

def read_name_val(file):
  f = open(file)
  r = {'_file': file[:-5], '_desc': file}
  rx = re.compile(r"^([^:]+)\s*:(.*)$")
  for l in f.xreadlines():
    if l == "END\n":
      f.close()
      return r
    m = rx.search(l)
    if m:
      r[m.group(1)] = string.strip(m.group(2))
    else:
      break
  f.close()
  return None

def scp_file(src, target):
  global problem
  f = os.popen("scp -v -B -p %s %s 2>&1 < /dev/null" % (src, target))
  problem = f.read()
  return f.close()

def copy_file(src, target):
  try:
    shutil.copyfile(src, target)
    return 0
  except:
    global problem
    exctype, value = sys.exc_info()[:2]
    problem = "cannot copy file: %s" % format_exception_only(exctype, value)
    return 1

def rsync_file(src, user, password, host, path):
  global problem
  # FIXME: use --password-file?
  f = os.popen("RSYNC_PASSWORD='%s' rsync --verbose --archive %s %s@%s::%s 2>&1 < /dev/null" \
                % (password, src, user, host, path))
  problem = f.read()
  return f.close()
  
def send_file(src, target):
  log.notice("sending %s" % target)
  m = re.match('rsync://([^@:]+):([^@]+)@([^/:]+)(:|/)(.*)', target)
  if m:
    return rsync_file(src, user = m.group(1), 
                           password = m.group(2), 
                           host = m.group(3),
                           path = m.group(5))
  if target != "" and target[0] == '/':
    return copy_file(src, target)
  m = re.match('scp://([^@:]+@[^/:]+)(:|)(.*)', target)
  if m:
    return scp_file(src, m.group(1) + ":" + m.group(3))
  log.alert("unsupported protocol: %s" % target)
  # pretend everything went OK, so file is removed from queue,
  # and doesn't cause any additional problems
  return 0

def maybe_flush_queue(dir):
  retry_delay = 0
  try:
    f = open(dir + "retry-at")
    last_retry = int(string.strip(f.readline()))
    retry_delay = int(string.strip(f.readline()))
    f.close()
    if last_retry + retry_delay > time.time():
      return
    os.unlink(dir + "retry-at")
  except:
    pass
    
  status.push("flushing %s" % dir)

  if flush_queue(dir):
    f = open(dir + "retry-at", "w")
    if retry_delay in retries_times:
      idx = retries_times.index(retry_delay)
      if idx < len(retries_times) - 1: idx += 1
    else:
      idx = 0
    f.write("%d\n%d\n" % (time.time(), retries_times[idx]))
    f.close()

  status.pop()

def flush_queue(dir):
  q = []
  for f in glob.glob(dir + "/*.desc"):
    d = read_name_val(f)
    if d != None: q.append(d)
  def mycmp(x, y):
    return cmp(x['Time'], y['Time'])
  q.sort(mycmp)
  
  error = None
  remaining = q
  for d in q:
    if send_file(d['_file'], d['Target']):
      error = d
      break
    if d.has_key('Store-desc') and d['Store-desc'] == "yes":
      if send_file(d['_desc'], d['Target'] + ".desc"):
        error = d
        break
    os.unlink(d['_file'])
    os.unlink(d['_desc'])
    remaining = q[1:]
    
  if error != None:
    users = {}
    for d in remaining:
      if d.has_key('Requester'):
        r = d['Requester']
        if r != "" and not users.has_key(r):
          users[r] = acl.user(r)
    e = [config.admin_email]
    for u in users.values(): e.append(u.mail_to())
    m = mailer.Message()
    m.set_headers(to = string.join(e, ", "), 
                  subject = "builder queue problem")
    m.write("there were problems sending files from queue %s:\n" % dir)
    m.write("problem: %s\n" % problem)
    m.send()
    return 1

  return 0

problem = ""

def main():
  init_conf("")
  maybe_flush_queue(path.buildlogs_queue_dir)
  maybe_flush_queue(path.ftp_queue_dir)

util.wrap(main)

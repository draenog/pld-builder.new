import string

import ftp
import stopwatch
from acl import acl

def unpackaged_files(b):
  msg = "warning: Installed (but unpackaged) file(s) found:\n"
  f = open(b.logfile)
  copy_mode = 0
  out = []
  for l in f.xreadlines():
    if l == msg:
      copy_mode = 1
      out.append(l)
    elif copy_mode:
      if l[0] != ' ':
        copy_mode = 0
      else:
        out.append(l)
  return out

def add_pld_builder_info(b):
  l = open(b.logfile, "a")
  l.write("Begin-PLD-Builder-Info\n")
  l.write("Build-Time: %s\n\n" % b.build_time)
  st = ftp.status()
  if st != "":
    l.write("Files queued for ftp:\n%s\n" % st)
  ftp.clear_status()
  l.writelines(unpackaged_files(b))
  l.write("End-PLD-Builder-Info\n")

def info_from_log(b, target):
  beg = "Begin-PLD-Builder-Info\n"
  end = "End-PLD-Builder-Info\n"
  f = open(b.logfile)
  copy_mode = 0
  need_header = 1
  for l in f.xreadlines():
    if l == beg:
      if need_header:
        need_header = 0
        target.write("\n--- %s:%s:\n" % (b.spec, b.branch))
      copy_mode = 1
    elif copy_mode:
      if l == end:
        copy_mode = 0
      else:
        target.write(l)
  
def send_report(r):
  def names(l): return map(lambda (b): b.spec, l)
  s_failed = filter(lambda (x): x.build_failed, r.batches)
  s_ok = filter(lambda (x): not x.build_failed, r.batches)
  subject = ""
  if s_failed != []:
    subject += " ERRORS: " + string.join(names(s_failed))
  if s_ok != []:
    subject += " OK: " + string.join(names(s_ok))
  
  m = acl.user(r.requester).message_to()
  m.set_headers(subject = subject[0:100])

  for b in r.batches:
    if b.build_failed and b.logfile == None:
      info = b.skip_reason
    elif b.build_failed: 
      info = "FAILED"
    else: 
      info = "OK"
    m.write("%s (%s): %s\n" % (b.spec, b.branch, info))

  for b in r.batches:
    if b.logfile != None:
      info_from_log(b, m)

  for b in r.batches:
    if b.build_failed and b.logfile != None:
      m.write("\n\n*** buildlog for %s\n" % b.spec)
      m.append_log(b.logfile)
      m.write("\n\n")
      
  m.send()

import string
import path

import ftp
import stopwatch
import mailer
from config import config

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
  
def send_report(r, is_src = False):
  s_failed = ' '.join([b.spec for b in r.batches if b.build_failed])
  s_ok = ' '.join([b.spec for b in r.batches if not b.build_failed])

  if s_failed: s_failed = "ERRORS: %s" % s_failed
  if s_ok: s_ok = "OK: %s" % s_ok

  subject = ' '.join((s_failed, s_ok))
  
  m = mailer.Message()
  m.set_headers(to = r.requester_email,
                cc = config.builder_list,
                subject = subject[0:100])
  if is_src:
    m.set_header("Message-ID", "<%s@pld.src.builder>" % r.id)
  else:
    m.set_header("References", "<%s@pld.src.builder>" % r.id)
    m.set_header("In-Reply-To", "<%s@pld.src.builder>" % r.id)

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
    if (b.is_command () or b.build_failed) and b.logfile != None:
      m.write("\n\n*** buildlog for %s\n" % b.spec)
      m.append_log(b.logfile)
      m.write("\n\n")
      
  m.send()

def send_cia_report(r, is_src = False):

  subject = 'DeliverXML'
  
  m = mailer.Message()
  m.set_headers(to = config.bot_email,
                subject = subject)
  m.set_header("Message-ID", "<%s@pld.src.builder>" % r.id)
  m.set_header("X-mailer", "$Id$")
  m.set_header("X-builder", "PLD")

  # get header of xml message from file
  f = open(path.root_dir + 'PLD_Builder/cia-head.xml')
  m.write(f.read())
  f.close()

  # write in iteration list and status of all processed files
  for b in r.batches:
    # Instead of hardcoded Ac information use some config variable
    m.write('<package name="%s" arch="%s">\n' % (b.spec, b.branch))
    if b.build_failed:
	    m.write('<success/>\n')
    else:
	    m.write('<failed/>\n')
    m.write('</package>\n')

  # get footer of xml message from file
  f = open(path.root_dir + 'PLD_Builder/cia-foot.xml')
  m.write(f.read())
  f.close()
	    
  # send the e-mail
  m.send()

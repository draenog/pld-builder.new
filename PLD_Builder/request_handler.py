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
from config import config, init_conf

def check_double_id(id):
  id_nl = id + "\n"
  
  ids = open(path.processed_ids_file)
  for i in ids.xreadlines():
    if i == id_nl:
      # FIXME: security email here?
      log.alert("request %s already processed" % id)
      return 1
  ids.close()
  
  ids = open(path.processed_ids_file, "a")
  ids.write(id_nl)
  ids.close()

  return 0

def handle_group(r, user):
  def fail_mail(msg):
    if len(r.batches) >= 1:
      spec = r.batches[0].spec
    else:
      spec = "None.spec"
    log.error("%s: %s" % (spec, msg))
    m = user.message_to()
    m.set_headers(subject = "building %s failed" % spec)
    m.write_line(msg)
    m.send()
  
  lock("request")
  if check_double_id(r.id):
    return
    
  if not user.can_do("src", config.builder):
    fail_mail("user %s is not allowed to src:%s" \
                % (user.get_login(), config.builder))
    return
    
  for batch in r.batches:
    for bld in batch.builders:
      if not user.can_do("binary", bld):
        fail_mail("user %s is not allowed to binary:%s" \
                        % (user.get_login(), bld))
        return

  r.requester = user.get_login()
  r.time = time.time()
  log.notice("queued %s from %s" % (r.id, user.get_login()))
  q = B_Queue(path.queue_file)
  q.lock(0)
  q.read()
  q.add(r)
  q.write()
  q.unlock()

def handle_request(f):
  sio = StringIO.StringIO()
  sio.write(f.read())
  sio.seek(0)
  (em, body) = gpg.verify_sig(sio)
  user = acl.user_by_email(em)
  if user == None:
    # FIXME: security email here
    log.alert("invalid signature, or not in acl %s" % em)
    return
  r = request.parse_request(body)
  if r.kind == 'group':
    handle_group(r, user)
  else:
    msg = "%s: don't know how to handle requests of this kind '%s'" \
                % (user.get_login(), r.kind)
    log.alert(msg)
    m = user.message_to()
    m.set_headers(subject = "unknown request")
    m.write_line(msg)
    m.send()

def main():
  init_conf("src")
  handle_request(sys.stdin)
  sys.exit(0)

main()

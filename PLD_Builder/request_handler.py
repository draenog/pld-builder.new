import email
import string
import time
import os
import StringIO

import gpg
import request
import log
import path
from acl import acl
from lock import lock
from bqueue import B_Queue

def check_double_id(id):
  id_nl = id + "\n"
  
  ids = open(path.processed_ids_file)
  for i in ids.xreadlines():
    if i == id_nl:
      # FIXME: security email here
      log.alert("request %s already processed" % r.id)
      return 1
  ids.close()
  
  ids = open(path.processed_ids_file, "a")
  ids.write(id_nl)
  ids.close()

  return 0

def handle_group(r):
  lock("request")
  user = r.acl_user
  if check_double_id(r.id):
    return
    
  if not user.can_do("src", "src"):
    msg ="user %s is not allowed to src:src" % (user.get_login())
    log.error(msg)
    user.notify_about_failure(msg)
    return
    
  for batch in r.batches:
    for bld in batch.builders:
      if not user.can_do("binary", bld):
        msg ="user %s is not allowed to binary:%s" % (user.get_login(), bld)
        log.error(msg)
        user.notify_about_failure(msg)
        return

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
  user = acl.user(em)
  if user == None:
    # FIXME: security email here
    log.alert("invalid signature, or not in acl %s" % em)
    return
  r = request.parse_request(body)
  r.acl_user = user
  if r.kind == 'group':
    handle_group(r)
  else:
    msg = "%s: don't know how to handle requests of this kind '%s'" \
                % (user.get_login(), r.kind)
    log.alert(msg)
    user.notify_about_failure(msg)

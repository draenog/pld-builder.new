import string
import os
import atexit

import notify
import path
import util
import chroot
import stopwatch
import report
import log
import buildlogs
import status

def build_all(r, build_fnc):
  status.email = r.requester_email
  notify.begin(r)
  tmp = path.spool_dir + util.uuid() + "/"
  r.tmp_dir = tmp
  os.mkdir(tmp)
  atexit.register(util.clean_tmp, tmp)

  log.notice("started processing %s" % r.id)
  r.chroot_files = []
  r.some_ok = 0
  for batch in r.batches:
    can_build = 1
    failed_dep = ""
    for dep in batch.depends_on:
      if dep.build_failed:
        can_build = 0
        failed_dep = dep.spec
     
    if can_build:
      log.notice("building %s" % batch.spec)
      stopwatch.start()
      batch.logfile = tmp + batch.spec + ".log"
      batch.build_failed = build_fnc(r, batch)
      if batch.build_failed:
        log.notice("building %s FAILED" % batch.spec)
        notify.add_batch(batch, "FAIL")
      else:
        r.some_ok = 1
        log.notice("building %s OK" % batch.spec)
        notify.add_batch(batch, "OK")
      batch.build_time = stopwatch.stop()
      report.add_pld_builder_info(batch)
      buildlogs.add(batch.logfile, failed = batch.build_failed)
    else:
      batch.build_failed = 1
      batch.skip_reason = "SKIPED [%s failed]" % failed_dep
      batch.logfile = None
      batch.build_time = ""
      log.notice("building %s %s" % (batch.spec, batch.skip_reason))
      notify.add_batch(batch, "SKIP")
      
  buildlogs.flush()
  chroot.run("rm -f %s" % string.join(r.chroot_files))

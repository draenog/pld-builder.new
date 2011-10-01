# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

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
from config import config, init_conf



def run_command(batch):
    # we want to keep "skip" in queue.html
    command = batch.command

    # rewrite special "skip:BUILD_ID into touch
    if command[:5] == "skip:":
        c = ""
        for id in command[5:].split(','):
            if os.path.isdir(path.srpms_dir + '/' + id):
                c = c + "echo skip:%s;\n" % (id)
                c = c + "touch %s/%s/skipme;\n" % (path.srpms_dir, id)
            else:
                c = c + "echo %s is not valid build-id;\n" % (id)
        command = c

    if "no-chroot" in batch.command_flags:
        # TODO: the append here by shell hack should be solved in python
        c = "(%s) >> %s 2>&1" % (command, batch.logfile)
        f = os.popen(c)
        for l in f.xreadlines():
            pass
        r = f.close()
        if r == None:
            return 0
        else:
            return r
    else:
        user = "root"
        if "as-builder" in batch.command_flags:
            user = "builder"
        return chroot.run(command, logfile = batch.logfile, user = user)

def build_all(r, build_fnc):
    status.email = r.requester_email
    notify.begin(r)
    tmp = path.build_dir + '/' + util.uuid() + "/"
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

        if batch.is_command() and can_build:
            batch.logfile = tmp + "command"
            if config.builder in batch.builders:
                log.notice("running %s" % batch.command)
                stopwatch.start()
                batch.build_failed = run_command(batch)
                if batch.build_failed:
                    log.notice("running %s FAILED" % batch.command)
                    notify.add_batch(batch, "FAIL")
                else:
                    r.some_ok = 1
                    log.notice("running %s OK" % batch.command)
                    notify.add_batch(batch, "OK")
                batch.build_time = stopwatch.stop()
                report.add_pld_builder_info(batch)
                buildlogs.add(batch.logfile, failed = batch.build_failed, id=r.id)
            else:
                log.notice("not running command, not for me.")
                batch.build_failed = 0
                batch.log_line("queued command %s for other builders" % batch.command)
                r.some_ok = 1
                buildlogs.add(batch.logfile, failed = batch.build_failed, id=r.id)
        elif can_build:
            log.notice("building %s" % batch.spec)
            stopwatch.start()
            batch.logfile = tmp + batch.spec + ".log"
            batch.gb_id=r.id
            batch.requester=r.requester
            batch.requester_email=r.requester_email
            batch.build_failed = build_fnc(r, batch)
            if batch.build_failed:
                log.notice("building %s FAILED (%s)" % (batch.spec, batch.build_failed))
                notify.add_batch(batch, batch.build_failed)
            else:
                r.some_ok = 1
                log.notice("building %s OK" % (batch.spec))
                notify.add_batch(batch, "OK")
            batch.build_time = stopwatch.stop()
            report.add_pld_builder_info(batch)
            buildlogs.add(batch.logfile, failed = batch.build_failed, id=r.id)
        else:
            batch.build_failed = 1
            batch.skip_reason = "SKIPED [%s failed]" % failed_dep
            batch.logfile = None
            batch.build_time = ""
            log.notice("building %s %s" % (batch.spec, batch.skip_reason))
            notify.add_batch(batch, "SKIP")

    buildlogs.flush()
    chroot.run("rm -f %s" % string.join(r.chroot_files))

# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import email
import string
import time
import os
import StringIO
import sys
import fnmatch

import gpg
import request
import log
import path
import util
import wrap
import status
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
    lockf = None
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
    
    lockf = lock("request")
    if check_double_id(r.id):
        lockf.close()
        return

    for batch in r.batches:

        if not user.can_do("src", config.builder, batch.branch):
            fail_mail("user %s is not allowed to src:%s:%s" \
                        % (user.get_login(), config.builder, batch.branch))
            lockf.close()
            return

        if 'test-build' in r.flags and 'upgrade' in r.flags:
            fail_mail("it's forbidden to upgrade from a test build")
            lockf.close()
            return

        if "upgrade" in r.flags and not user.can_do("upgrade", config.builder, batch.branch):
            fail_mail("user %s is not allowed to upgrade:%s:%s" \
                        % (user.get_login(), config.builder, batch.branch))
            lockf.close()
            return

        # src builder handles only special commands
        if batch.is_command() and (batch.command in ["cvs up"] or batch.command[:5] == "skip:"  or config.builder in batch.builders):
            batch.expand_builders(config.binary_builders + [config.src_builder])
        else:
            batch.expand_builders(config.binary_builders)

        if not batch.is_command() and config.builder in batch.builders:
            batch.builders.remove(config.builder)

        for bld in batch.builders:
            batch.builders_status[bld] = '?'
            batch.builders_status_time[bld] = time.time()
            if bld not in config.binary_builders and bld != config.builder:
                fail_mail("I (src rpm builder '%s') do not handle binary builder '%s', only '%s'" % \
                        (config.builder, bld, string.join(config.binary_builders)))
                lockf.close()
                return
            if batch.is_command():
                if "no-chroot" in batch.command_flags:
                    if not user.can_do("command-no-chroot", bld):
                        fail_mail("user %s is not allowed to command-no-chroot:%s" \
                                % (user.get_login(), bld))
                        lockf.close()
                        return
                if not user.can_do("command", bld):
                    fail_mail("user %s is not allowed to command:%s" \
                                % (user.get_login(), bld))
                    lockf.close()
                    return
            elif not user.can_do("binary", bld, batch.branch):
                pkg = batch.spec
                if pkg.endswith(".spec"):
                    pkg = pkg[:-5]
                if not user.can_do("binary-" + pkg, bld, batch.branch):
                    fail_mail("user %s is not allowed to binary-%s:%s:%s" \
                                % (user.get_login(), pkg, bld, batch.branch))
                    lockf.close()
                    return
    
    r.priority = user.check_priority(r.priority,config.builder)
    r.requester = user.get_login()
    r.requester_email = user.mail_to()
    r.time = time.time()
    log.notice("queued %s from %s" % (r.id, user.get_login()))
    q = B_Queue(path.queue_file)
    q.lock(0)
    q.read()
    q.add(r)
    q.write()
    q.unlock()
    lockf.close()

def handle_notification(r, user):
    if not user.can_do("notify", r.builder):
        log.alert("user %s is not allowed to notify:%s" % (user.login, r.builder))
    q = B_Queue(path.req_queue_file)
    q.lock(0)
    q.read()
    not_fin = filter(lambda (r): not r.is_done(), q.requests)
    r.apply_to(q)
    for r in not_fin:
        if r.is_done():
            util.clean_tmp(path.srpms_dir + '/' + r.id)
    now = time.time()
    def leave_it(r):
        # for ,,done'' set timeout to 4d
        if r.is_done() and r.time + 4 * 24 * 60 * 60 < now:
            return False
        # and for not ,,done'' set it to 20d
        if r.time + 20 * 24 * 60 * 60 < now:
            util.clean_tmp(path.srpms_dir + '/' + r.id)
            return False
        return True
    q.requests = filter(leave_it, q.requests)
    q.write()
    q.dump(open(path.queue_stats_file, "w"))
    q.dump_html(open(path.queue_html_stats_file, "w"))
    os.chmod(path.queue_html_stats_file, 0644)
    os.chmod(path.queue_stats_file, 0644)
    q.write_signed(path.req_queue_signed_file)
    os.chmod(path.req_queue_signed_file, 0644)
    q.unlock()

def handle_request(req, filename = None):
    if req == '':
        log.alert('Empty body received. Filename: %s' % filename)
        return False

    keys = gpg.get_keys(req)
    (em, body) = gpg.verify_sig(req)
    if not em:
        log.alert("Invalid signature, missing/untrusted key. Keys in gpg batch: '%s'" % keys)
        return False
    user = acl.user_by_email(em)
    if user == None:
        # FIXME: security email here
        log.alert("'%s' not in acl. Keys in gpg batch: '%s'" % (em, keys))
        return False

    acl.set_current_user(user)
    status.push("request from %s" % user.login)
    r = request.parse_request(body)
    if r.kind == 'group':
        handle_group(r, user)
    elif r.kind == 'notification':
        handle_notification(r, user)
    else:
        msg = "%s: don't know how to handle requests of this kind '%s'" \
                        % (user.get_login(), r.kind)
        log.alert(msg)
        m = user.message_to()
        m.set_headers(subject = "unknown request")
        m.write_line(msg)
        m.send()
    status.pop()
    return True

def handle_request_main(req, filename = None):
    init_conf("src")
    status.push("handling email request")
    ret = handle_request(req, filename = filename)
    status.pop()
    return ret

def main():
    sys.exit(not handle_request_main(sys.stdin.read()))

if __name__ == '__main__':
    wrap.wrap(main)

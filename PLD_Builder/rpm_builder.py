# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import sys
import os
import atexit
import time
import string
import urllib

from config import config, init_conf
from bqueue import B_Queue
import lock
import util
import loop
import path
import status
import log
import chroot
import ftp
import buildlogs
import notify
import build
import report
import upgrade
import install_br

# *HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*
import socket

socket.myorigsocket=socket.socket

def mysocket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
    s=socket.myorigsocket(family, type, proto)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    return s

socket.socket=mysocket
# *HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*HACK*

# this code is duplicated in srpm_builder, but we
# might want to handle some cases differently here
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
    return ret

def fetch_src(r, b):
    src_url = config.control_url + "/srpms/" + r.id + "/" + b.src_rpm
    b.log_line("fetching %s" % src_url)
    start = time.time()
    good=False
    while not good:
        try:
            good=True
            f = urllib.urlopen(src_url)
        except IOError, error:
            if error[1][0] == 60 or error[1][0] == 110 or error[1][0] == -3 or error[1][0] == 111 or error[1][0] == 61:
                good=False
                b.log_line("unable to connect... trying again")
            else:
                f = urllib.urlopen(src_url) # So we get the exception logged :)

    o = chroot.popen("cat > %s" % b.src_rpm, mode = "w")
    bytes = util.sendfile(f, o)
    f.close()
    o.close()
    t = time.time() - start
    if t == 0:
        b.log_line("fetched %d bytes" % bytes)
    else:
        b.log_line("fetched %d bytes, %.1f K/s" % (bytes, bytes / 1024.0 / t))

def prepare_env():
    chroot.run("test ! -f /proc/uptime && mount /proc", 'root')

def build_rpm(r, b):
    status.push("building %s" % b.spec)
    b.log_line("request from: %s" % r.requester)
    b.log_line("started at: %s" % time.asctime())
    fetch_src(r, b)
    b.log_line("installing srpm: %s" % b.src_rpm)
    res = chroot.run("rpm -U %s" % b.src_rpm, logfile = b.logfile)
    chroot.run("rm -f %s" % b.src_rpm, logfile = b.logfile)
    b.files = []
    tmpdir = "/tmp/B." + b.b_id[0:6]
    if res:
        b.log_line("error: installing src rpm failed")
        res = 1
    else:
        prepare_env()
        chroot.run("install -m 700 -d %s" % tmpdir)
        rpmbuild_opt = "%s --target %s-pld-linux" % (b.bconds_string(), config.arch)
        cmd = "cd rpm/SPECS; TMPDIR=%s nice -n %s rpmbuild -bb %s %s" % \
                    (tmpdir, config.nice, rpmbuild_opt, b.spec)
        if ("no-install-br" not in r.flags) and install_br.install_br(r, b):
            res = 1
        else:
            b.log_line("building RPM using: %s" % cmd)
            res = chroot.run(cmd, logfile = b.logfile)
            files = util.collect_files(b.logfile)
            if len(files) > 0:
                r.chroot_files.extend(files)
            else:
                b.log_line("error: No files produced.")
                res = 1 # FIXME: is it error?
            b.files = files
    chroot.run("rm -rf %s; cd rpm/SPECS; rpmbuild --nodeps --nobuild " \
                         "--clean --rmspec --rmsource %s" % \
                         (tmpdir, b.spec), logfile = b.logfile)
    chroot.run("rm -rf $HOME/rpm/BUILD/*")

    def ll(l):
        util.append_to(b.logfile, l)
 
    if b.files != []:
        if "test-build" not in r.flags:
            chroot.run("cp -f %s /spools/ready/; poldek --nodiff --mkidxz " \
                     "-s /spools/ready/" % \
                     string.join(b.files), logfile = b.logfile, user = "root")
        else:
            ll("test-build: not copying to /spools/ready/")
        ll("Begin-PLD-Builder-Info")
        if "upgrade" in r.flags:
            b.upgraded = upgrade.upgrade_from_batch(r, b)
        else:
            ll("not upgrading")
        ll("End-PLD-Builder-Info")

    for f in b.files:
        local = r.tmp_dir + os.path.basename(f)
        chroot.cp(f, outfile = local, rm = True)
        ftp.add(local)

    def uploadinfo(b):
        c="file:SRPMS:%s\n" % b.src_rpm
        for f in b.files:
            c=c + "file:ARCH:%s\n" % os.path.basename(f)
        c=c + "END\n"
        return c

    if config.gen_upinfo and b.files != [] and 'test-build' not in r.flags:
        fname = r.tmp_dir + b.src_rpm + ".uploadinfo"
        f = open(fname, "w")
        f.write(uploadinfo(b))
        f.close()
        ftp.add(fname, "uploadinfo")

    status.pop()

    return res

def handle_request(r):
    ftp.init(r)
    buildlogs.init(r)
    build.build_all(r, build_rpm)
    report.send_report(r, is_src = False)
    ftp.flush()
    notify.send()

def check_load():
    do_exit = 0
    try:
        f = open("/proc/loadavg")
        if float(string.split(f.readline())[2]) > config.max_load:
            do_exit = 1
    except:
        pass
    if do_exit:
        sys.exit(0)

def main_for(builder):
    init_conf(builder)
    # allow only one build in given builder at once
    if not lock.lock("building-rpm-for-%s" % config.builder, non_block = 1):
        return
    # don't kill server
    check_load()
    # not more then job_slots builds at once
    locked = 0
    for slot in range(config.job_slots):
        if lock.lock("building-rpm-slot-%d" % slot, non_block = 1):
            locked = 1
            break
    if not locked:
        return

    status.push("picking request for %s" % config.builder)
    q = B_Queue(path.queue_file + "-" + config.builder)
    q.lock(0)
    q.read()
    if q.requests == []:
        q.unlock()
        return
    req = pick_request(q)
    q.unlock()
    status.pop()

    # record fact that we got lock for this builder, load balancer
    # will use it for fair-queuing
    l = lock.lock("got-lock")
    f = open(path.got_lock_file, "a")
    f.write(config.builder + "\n")
    f.close()
    l.close()
    
    msg = "handling request %s (%d) for %s from %s" \
            % (req.id, req.no, config.builder, req.requester)
    log.notice(msg)
    status.push(msg)
    handle_request(req)
    status.pop()

    def otherreqs(r):
        if r.no==req.no:
            return False
        else:
            return True

    q = B_Queue(path.queue_file + "-" + config.builder)
    q.lock(0)
    q.read()
    previouslen=len(q.requests)
    q.requests=filter(otherreqs, q.requests)
    if len(q.requests)<previouslen:
        q.write()
    q.unlock()
    
def main():
    if len(sys.argv) < 2:
        raise "fatal: need to have builder name as first arg"
    return main_for(sys.argv[1])
    
if __name__ == '__main__':
    loop.run_loop(main)

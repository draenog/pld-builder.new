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
import install

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
            raise Exception, "non-group requests"
        pri_diff = cmp(r1.priority, r2.priority)
        if pri_diff == 0:
            return cmp(r1.time, r2.time)
        else:
            return pri_diff
    q.requests.sort(mycmp)
    ret = q.requests[0]
    return ret

def check_skip_build(r):
    src_url = config.control_url + "/srpms/" + r.id + "/skipme"
    good  = True
    b.log_line("checking if we should skip the build")
    while not good:
        try:
            good=True
            f = urllib.urlopen(src_url)
        except IOError, error:
            if error[1][0] == 60 or error[1][0] == 110 or error[1][0] == -3 or error[1][0] == 111 or error[1][0] == 61:
                good=False
                b.log_line("unable to connect... trying again")
                continue
            else:
                return False
        http_code = f.getcode()
        if http_code == 200:
            f.close()
            b.log_line("checking if we should skip the build: yes")
            return True
    return False

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
                continue
            else:
                raise
        http_code = f.getcode()
        if http_code != 200:
                # fail in a way where cron job will retry
                msg = "unable to fetch file, http code: %d" % http_code
                b.log_line(msg)
                f.close()
                raise IOError, msg

    o = chroot.popen("cat > %s" % b.src_rpm, mode = "w")

    try:
        bytes = util.sendfile(f, o)
    except IOError, e:
        b.log_line("error: unable to write to `%s': %s" % (b.src_rpm, e))
        raise

    f.close()
    o.close()
    t = time.time() - start
    if t == 0:
        b.log_line("fetched %d bytes" % bytes)
    else:
        b.log_line("fetched %d bytes, %.1f K/s" % (bytes, bytes / 1024.0 / t))

def prepare_env():
    chroot.run("test ! -f /proc/uptime && mount /proc", 'root')
    chroot.run("test ! -e /dev/full && mknod /dev/full c 1 7 && chmod 666 /dev/full", 'root')
    chroot.run("test ! -e /dev/null && mknod /dev/null c 1 3 && chmod 666 /dev/null", 'root')
    chroot.run("test ! -e /dev/random && mknod /dev/random c 1 8 && chmod 644 /dev/random", 'root')
    chroot.run("test ! -e /dev/urandom && mknod /dev/urandom c 1 9 && chmod 644 /dev/urandom", 'root')
    chroot.run("test ! -e /dev/zero && mknod /dev/zero c 1 5 && chmod 666 /dev/zero", 'root')
    # try to limit network access for builder account
    chroot.run("/bin/setfacl -m u:builder:--- /etc/resolv.conf", 'root')

def build_rpm(r, b):
    status.push("building %s" % b.spec)
    b.log_line("request from: %s" % r.requester)

    if check_skip_build(r):
        b.log_line("build skipped due to src builder request")
        res = "SKIP_REQUESTED"
        return res

    b.log_line("started at: %s" % time.asctime())
    fetch_src(r, b)
    b.log_line("installing srpm: %s" % b.src_rpm)
    res = chroot.run("rpm -U %s" % b.src_rpm, logfile = b.logfile)
    chroot.run("rm -f %s" % b.src_rpm, logfile = b.logfile)
    b.files = []
    tmpdir = "/tmp/B." + b.b_id[0:6]
    if res:
        b.log_line("error: installing src rpm failed")
        res = "FAIL_SRPM_INSTALL"
    else:
        prepare_env()
        chroot.run("install -m 700 -d %s" % tmpdir)

        b.default_target(config.arch)
        rpmbuild_opt = "%s %s %s" % (b.target_string(), b.kernel_string(), b.bconds_string())
        # check for build arch before filling BR
        cmd = "cd rpm/SPECS; TMPDIR=%s nice -n %s rpmbuild -bp --short-circuit --nodeps --define 'prep exit 0' %s %s" % \
            (tmpdir, config.nice, rpmbuild_opt, b.spec)
        res = chroot.run(cmd, logfile = b.logfile)
        if res:
            res = "UNSUPP"
            b.log_line("error: build arch check (%s) failed" % cmd)

        if not res:
            if ("no-install-br" not in r.flags) and not install.uninstall_self_conflict(b):
                res = "FAIL_DEPS_UNINSTALL"
            if ("no-install-br" not in r.flags) and not install.install_br(r, b):
                res = "FAIL_DEPS_INSTALL"
            if not res:
                max_jobs = max(min(int(os.sysconf('SC_NPROCESSORS_ONLN') * 1.5), config.max_jobs), 1)
                if r.max_jobs > 0:
                    max_jobs = max(min(config.max_jobs, r.max_jobs), 1)
                cmd = "cd rpm/SPECS; TMPDIR=%s nice -n %s rpmbuild -bb --define '_smp_mflags -j%d' %s %s" % \
                            (tmpdir, config.nice, max_jobs, rpmbuild_opt, b.spec)
                b.log_line("building RPM using: %s" % cmd)
                begin_time = time.time()
                res = chroot.run(cmd, logfile = b.logfile)
                end_time = time.time()
                b.log_line("ended at: %s, done in %s" % (time.asctime(), time.strftime("%Hh %Mm %Ss", time.gmtime(end_time - begin_time))))
                if res:
                    res = "FAIL"
                files = util.collect_files(b.logfile)
                if len(files) > 0:
                    r.chroot_files.extend(files)
                else:
                    b.log_line("error: No files produced.")
                    last_section = util.find_last_section(b.logfile)
                    if last_section == None:
                        res = "FAIL"
                    else:
                        res = "FAIL_%s" % last_section.upper()
                b.files = files

    chroot.run("rm -rf %s; cd rpm/SPECS; rpmbuild --nodeps --nobuild " \
                         "--clean --rmspec --rmsource %s" % \
                         (tmpdir, b.spec), logfile = b.logfile)
    chroot.run("rm -rf $HOME/rpm/BUILD/*")

    def ll(l):
        util.append_to(b.logfile, l)
 
    if b.files != []:
        rpm_cache_dir = config.rpm_cache_dir
        if "test-build" not in r.flags:
            # NOTE: copying to cache dir doesn't mean that build failed, so ignore result
            b.log_line("copy rpm files to cache_dir: %s" % rpm_cache_dir)
            chroot.run(
                    "cp -f %s %s && poldek --mo=nodiff --mkidxz -s %s/" % \
                        (string.join(b.files), rpm_cache_dir, rpm_cache_dir),
                     logfile = b.logfile, user = "root"
            )
        else:
            ll("test-build: not copying to " + rpm_cache_dir)
        ll("Begin-PLD-Builder-Info")
        if "upgrade" in r.flags:
            b.upgraded = install.upgrade_from_batch(r, b)
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
    notify.send(r)

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
    msg = ""

    init_conf(builder)

    q = B_Queue(path.queue_file + "-" + config.builder)
    q.lock(0)
    q.read()
    if q.requests == []:
        q.unlock()
        return
    req = pick_request(q)
    q.unlock()

    # high priority tasks have priority < 0, normal tasks >= 0
    if req.priority >= 0:

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

        # record fact that we got lock for this builder, load balancer
        # will use it for fair-queuing
        l = lock.lock("got-lock")
        f = open(path.got_lock_file, "a")
        f.write(config.builder + "\n")
        f.close()
        l.close()
    else:
        msg = "HIGH PRIORITY: "
    
    msg += "handling request %s (%d) for %s from %s, priority %s" \
            % (req.id, req.no, config.builder, req.requester, req.priority)
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
        raise Exception, "fatal: need to have builder name as first arg"
    return main_for(sys.argv[1])
    
if __name__ == '__main__':
    loop.run_loop(main)

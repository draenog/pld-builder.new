# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import glob
import re
import string
import os
import time
import shutil
import sys
import traceback
import urllib2

from config import config, init_conf
import mailer
import path
import log
import loop
import status
import lock

retries_times = [5 * 60, 5 * 60, 10 * 60, 10 * 60, 30 * 60, 60 * 60]

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
    global problems
    f = os.popen("scp -v -B %s %s 2>&1 < /dev/null" % (src, target))
    p = f.read()
    ret = f.close()
    if ret:
        problems[src] = p
    return ret

def copy_file(src, target):
    try:
        shutil.copyfile(src, target)
        return 0
    except:
        global problems
        exctype, value = sys.exc_info()[:2]
        problems[src] = "cannot copy file: %s" % traceback.format_exception_only(exctype, value)
        return 1

def rsync_file(src, target, host):
    global problems

    p = open(path.rsync_password_file, "r")
    password = ""
    for l in p.xreadlines():
        l = string.split(l)
        if len(l) >= 2 and l[0] == host:
            password = l[1]
    p.close()

    # NOTE: directing STDIN to /dev/null, does not make rsync to skip asking
    # password, it opens /dev/tty and still asks if password is needed and
    # missing, therefore we always set RSYNC_PASSWORD env var
    os.environ["RSYNC_PASSWORD"] = password
    rsync = "rsync --verbose --archive"
    f = os.popen("%s %s %s 2>&1" % (rsync, src, target))
    p = f.read()
    ret = f.close()
    if ret:
        problems[src] = p
    del os.environ["RSYNC_PASSWORD"];
    return ret

def rsync_ssh_file(src, target):
    global problems
    rsync = "rsync --verbose --archive -e ssh"
    f = os.popen("%s %s %s 2>&1 < /dev/null" % (rsync, src, target))
    p = f.read()
    ret = f.close()
    if ret:
        problems[src] = p
    return ret

def post_file(src, url):
    global problems
    try:
        f = open(src, 'r')
        data = f.read()
        f.close()
        req = urllib2.Request(url, data)
        req.add_header('X-Filename', os.path.basename(src))
        f = urllib2.urlopen(req)
        f.close()
    except Exception, e:
        problems[src] = e
        return e
    return 0

def send_file(src, target):
    global problems
    try:
        log.notice("sending %s to %s (size %d bytes)" % (src, target, os.stat(src).st_size))
        m = re.match('rsync://([^/]+)/.*', target)
        if m:
            return not rsync_file(src, target, host = m.group(1))
        if target != "" and target[0] == '/':
            return not copy_file(src, target)
        m = re.match('scp://([^@:]+@[^/:]+)(:|)(.*)', target)
        if m:
            return not scp_file(src, m.group(1) + ":" + m.group(3))
        m = re.match('ssh\+rsync://([^@:]+@[^/:]+)(:|)(.*)', target)
        if m:
            return not rsync_ssh_file(src, m.group(1) + ":" + m.group(3))
        m = re.match('http://.*', target)
        if m:
            return not post_file(src, target)
        log.alert("unsupported protocol: %s" % target)
    except OSError, e:
        problems[src] = e
        log.error("send_file(%s, %s): %s" % (src, target, e))
        return False
    return True

def maybe_flush_queue(dir):
    retry_delay = 0
    try:
        f = open(dir + "/retry-at")
        last_retry = int(string.strip(f.readline()))
        retry_delay = int(string.strip(f.readline()))
        f.close()
        if last_retry + retry_delay > time.time():
            return
        os.unlink(dir + "/retry-at")
    except:
        pass

    status.push("flushing %s" % dir)

    if flush_queue(dir):
        f = open(dir + "/retry-at", "w")
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
    os.chdir(dir)
    for f in glob.glob(dir + "/*.desc"):
        d = read_name_val(f)
        if d != None: q.append(d)
    def mycmp(x, y):
        rc = cmp(x['Time'], y['Time'])
        if rc == 0 and x.has_key('Type') and y.has_key('Type'):
            return cmp(x['Type'], y['Type'])
        else:
            return rc
    q.sort(mycmp)

    error = None
    # copy of q
    remaining = q[:]
    for d in q:
        if not send_file(d['_file'], d['Target']):
            error = d
            continue
        if os.access(d['_file'] + ".info", os.F_OK):
            if not send_file(d['_file'] + ".info", d['Target'] + ".info"):
                error = d
                continue
            os.unlink(d['_file'] + ".info")
        os.unlink(d['_file'])
        os.unlink(d['_desc'])
        remaining.remove(d)

    if error != None:
        emails = {}
        emails[config.admin_email] = 1
        pr = ""
        for src, msg in problems.iteritems():
            pr = pr + "[src: %s]\n\n%s\n" % (src, msg)
        for d in remaining:
            if d.has_key('Requester'):
                emails[d['Requester']] = 1
        e = emails.keys()
        m = mailer.Message()
        m.set_headers(to = string.join(e, ", "),
                      subject = "[%s] builder queue problem" % config.builder)
        m.write("there were problems sending files from queue %s:\n" % dir)
        m.write("problems:\n")
        m.write("%s\n" % pr)
        m.send()
        log.error("error sending files from %s:\n%s\n" % (dir, pr))
        return 1

    return 0

problems = {}

def main():
    if lock.lock("sending-files", non_block = 1) == None:
        return
    init_conf()
    maybe_flush_queue(path.notify_queue_dir)
    maybe_flush_queue(path.buildlogs_queue_dir)
    maybe_flush_queue(path.ftp_queue_dir)

if __name__ == '__main__':
    loop.run_loop(main)

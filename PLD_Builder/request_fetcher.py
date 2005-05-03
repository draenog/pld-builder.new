# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import string
import signal
import os
import urllib
import StringIO
import sys
import gzip

import path
import log
import status
import lock
import util
import gpg
import request
import loop
from acl import acl
from bqueue import B_Queue
from config import config, init_conf

last_count = 0

def alarmalarm(signum, frame):
    raise IOError, 'TCP connection hung'

def has_new(control_url):
    global last_count
    cnt_f = open(path.last_req_no_file)
    last_count = int(string.strip(cnt_f.readline()))
    cnt_f.close()
    f = None
    signal.signal(signal.SIGALRM, alarmalarm)
    signal.alarm(300)
    try:
        f = urllib.urlopen(control_url + "/max_req_no")
        count = int(string.strip(f.readline()))
        signal.alarm(0)
    except:
        signal.alarm(0)
        log.error("can't fetch %s" % (control_url + "/max_req_no"))
        sys.exit(1)
    res = 0
    if count != last_count:
        res = 1
    f.close()
    return res

def fetch_queue(control_url):
    signal.signal(signal.SIGALRM, alarmalarm)
    signal.alarm(300)
    try:
        f = urllib.urlopen(control_url + "/queue.gz")
        signal.alarm(0)
    except:
        signal.alarm(0)
        log.error("can't fetch %s" % (control_url + "/queue.gz"))
        sys.exit(1)
    sio = StringIO.StringIO()
    util.sendfile(f, sio)
    f.close()
    sio.seek(0)
    f = gzip.GzipFile(fileobj = sio)
    (signers, body) = gpg.verify_sig(f)
    u = acl.user_by_email(signers)
    if u == None:
        log.alert("queue.gz not signed with signature of valid user: %s" % signers)
        sys.exit(1)
    if not u.can_do("sign_queue", "all"):
        log.alert("user %s is not allowed to sign my queue" % u.login)
        sys.exit(1)
    body.seek(0)
    return request.parse_requests(body)

def handle_reqs(builder, reqs):
    qpath = path.queue_file + "-" + builder
    if not os.access(qpath, os.F_OK):
        util.append_to(qpath, "<queue/>\n")
    q = B_Queue(qpath)
    q.lock(0)
    q.read()
    for r in reqs:
        if r.kind != 'group': 
            raise 'handle_reqs: fatal: huh? %s' % r.kind
        need_it = 0
        for b in r.batches:
            if builder in b.builders:
                need_it = 1
        if need_it:
            log.notice("queued %s (%d) for %s" % (r.id, r.no, builder))
            q.add(r)
    q.write()
    q.unlock()

def main():
    lck = lock.lock("request_fetcher", non_block = True)
    if lck == None:
        sys.exit(1)
    init_conf()
    
    status.push("fetching requests")
    if has_new(config.control_url):
        q = fetch_queue(config.control_url)
        max_no = 0
        q_new = []
        for r in q:
            if r.no > max_no: 
                max_no = r.no
            if r.no > last_count:
                q_new.append(r)
        for b in config.binary_builders:
            handle_reqs(b, q_new)
        f = open(path.last_req_no_file, "w")
        f.write("%d\n" % max_no)
        f.close()
    status.pop()
    lck.close()
    
if __name__ == '__main__':
    # http connection is established (and few bytes transferred through it) 
    # each $secs seconds.
    loop.run_loop(main, secs = 10)

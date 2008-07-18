# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import email
import string
import time
import os
import StringIO
import sys
import re
import atexit

import gpg
import request
import log
import path
import util
import loop
import chroot
import ftp
import buildlogs
import status
import build
import report

from lock import lock
from bqueue import B_Queue
from config import config, init_conf

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
    q.requests = q.requests[1:]
    return ret
    
def store_binary_request(r):
    new_b = []
    for b in r.batches:
        if not b.build_failed: new_b.append(b)
    if new_b == []:
        return
    r.batches = new_b
    # store new queue and max_req_no for binary builders
    cnt_f = open(path.max_req_no_file, "r+")
    num = int(string.strip(cnt_f.read())) + 1
    r.no = num
    q = B_Queue(path.req_queue_file)
    q.lock(0)
    q.read()
    q.add(r)
    q.write()
    q.dump(open(path.queue_stats_file, "w"))
    q.dump_html(open(path.queue_html_stats_file, "w"))
    os.chmod(path.queue_stats_file, 0644)
    os.chmod(path.queue_html_stats_file, 0644)
    q.write_signed(path.req_queue_signed_file)
    os.chmod(path.req_queue_signed_file, 0644)
    q.unlock()
    cnt_f.seek(0)
    cnt_f.write("%d\n" % num)
    cnt_f.close()
    os.chmod(path.max_req_no_file, 0644)

def transfer_file(r, b):
    local = path.srpms_dir + r.id + "/" + b.src_rpm
    f = b.src_rpm_file
    # export files from chroot
    chroot.cp(f, outfile = local, rm = True)
    os.chmod(local, 0644)
    ftp.add(local)

    if config.gen_upinfo and 'test-build' not in r.flags:
        fname = path.srpms_dir + r.id + "/" + b.src_rpm + ".uploadinfo"
        f = open(fname, "w")
        f.write("info:build:%s:requester:%s\ninfo:build:%s:requester_email:%s\nfile:SRPMS:%s\nEND\n" % (b.gb_id, b.requester, b.gb_id, b.requester_email, b.src_rpm))
        f.close()
        ftp.add(fname, "uploadinfo")

def build_srpm(r, b):
    status.push("building %s" % b.spec)
    b.src_rpm = ""
    builder_opts = "-nu -nm --nodeps"
    if ("test-build" in r.flags) or b.branch and b.branch.startswith(config.tag_prefixes[0]):
                    tag_test=""
    else:
                    tag_test=" -Tp %s -tt" % (config.tag_prefixes[0],)
    cmd = ("cd rpm/SPECS; nice -n %s ./builder %s -bs %s -r %s %s %s %s 2>&1" %
             (config.nice, builder_opts, b.bconds_string(), b.branch, 
              tag_test, b.kernel_string(), b.spec))
    util.append_to(b.logfile, "request from: %s" % r.requester)
    util.append_to(b.logfile, "started at: %s" % time.asctime())
    util.append_to(b.logfile, "building SRPM using: %s\n" % cmd)
    res = chroot.run(cmd, logfile = b.logfile)
    util.append_to(b.logfile, "exit status %d" % res)
    files = util.collect_files(b.logfile)
    if len(files) > 0:
        if len(files) > 1:
            util.append_to(b.logfile, "error: More than one file produced: %s" % files)
            res = 1
        last = files[len(files) - 1]
        b.src_rpm_file = last
        b.src_rpm = os.path.basename(last)
        r.chroot_files.extend(files)
    else:
        util.append_to(b.logfile, "error: No files produced.")
        res = 1
    if res == 0 and not "test-build" in r.flags:
        for pref in config.tag_prefixes:
            util.append_to(b.logfile, "Tagging with prefix: %s" % pref)
            res = chroot.run("cd rpm/SPECS; ./builder -r %s -Tp %s -Tv %s" % \
                        (b.branch, pref, b.spec), logfile = b.logfile)
    if res == 0:
        transfer_file(r, b)
    chroot.run("cd rpm/SPECS; rpmbuild --nodeps --nobuild " \
                         "--clean --rmspec --rmsource %s" % \
                         b.spec, logfile = b.logfile)
    status.pop()
    return res

def handle_request(r):
    os.mkdir(path.srpms_dir + r.id)
    os.chmod(path.srpms_dir + r.id, 0755)
    ftp.init(r)
    buildlogs.init(r)
    build.build_all(r, build_srpm)
    report.send_report(r, is_src = True)
    report.send_cia_report(r, is_src = True)
    store_binary_request(r)
    ftp.flush()

def main():
    init_conf("src")
    if lock("building-srpm", non_block = 1) == None:
        return
    status.push("srpm: processing queue")
    q = B_Queue(path.queue_file)
    if not q.lock(1): return
    q.read()
    if q.requests == []: return
    r = pick_request(q)
    q.write()
    q.unlock()
    status.pop()
    status.push("srpm: handling request from %s" % r.requester)
    handle_request(r)
    status.pop()

if __name__ == '__main__':
    loop.run_loop(main)

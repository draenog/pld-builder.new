# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import sys
import os
import log
import string

def pkg_name(nvr):
    return re.match(r"(.+)-[^-]+-[^-]+", nvr).group(1)
    
def msg(m):
    sys.stderr.write(m)

def sendfile(src, dst):
    cnt = 0
    while 1:
        s = src.read(10000)
        if s == "": break
        cnt += len(s)
        dst.write(s)
    return cnt

def append_to(log, msg):
    f = open(log, "a")
    f.write("%s\n" % msg)
    f.close()

def clean_tmp(dir):
    # FIXME: use python
    os.system("rm -f %s/* 2>/dev/null; rmdir %s 2>/dev/null" % (dir, dir))

def uuid():
    f = os.popen("uuidgen 2>&1")
    u = string.strip(f.read())
    f.close()
    if len(u) != 36:
        raise "uuid: fatal, cannot generate uuid: %s" % u
    return u

def collect_files(log):
    f = open(log)
    rx = re.compile(r"^Wrote: (/home.*\.rpm)$")
    files = []
    for l in f.xreadlines():
        m = rx.search(l)
        if m:
            files.append(m.group(1))
    return files

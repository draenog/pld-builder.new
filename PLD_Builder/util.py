# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import sys
import os
import log
import string

def uuid_python():
    return str(uuid_random())

def uuid_external():
    f = os.popen("uuidgen 2>&1")
    u = string.strip(f.read())
    f.close()
    if len(u) != 36:
        raise Exception, "uuid: fatal, cannot generate uuid: %s" % u
    return u

# uuid module available in python >= 2.5
try:
    from uuid import uuid4 as uuid_random
except ImportError:
    uuid = uuid_external
else:
    uuid = uuid_python

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

def collect_files(log, basedir = "/home"):
    f = open(log, 'r')
    rx = re.compile(r"^Wrote: (%s.*\.rpm)$" % basedir)
    files = []
    for l in f.xreadlines():
        m = rx.search(l)
        if m:
            files.append(m.group(1))
    f.close()
    return files

def find_last_section(log):
    f = open(log, 'r')
    rx1 = re.compile(r"^Executing\(%(\w+)\).*$")
    rx2 = re.compile(r"^Processing (files):.*$")
    last_section = None
    for l in f:
        m = rx1.search(l)
        if not m:
            m = rx2.search(l)
        if m:
            last_section = m.group(1)
    f.close()
    return last_section

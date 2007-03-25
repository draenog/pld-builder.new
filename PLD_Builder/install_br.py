# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import string

import chroot

def install_br(r, b):
    tmpdir = "/tmp/BR." + b.b_id[0:6]
    chroot.run("install -m 700 -d %s" % tmpdir)
    cmd = "cd rpm/SPECS; TMPDIR=%s rpmbuild --nobuild %s %s 2>&1" \
                % (tmpdir, b.bconds_string(), b.spec)
    f = chroot.popen(cmd)
    rx = re.compile(r"^\s*([^\s]+) .*is needed by")
    needed = {}
    b.log_line("checking BR")
    for l in f.xreadlines():
        b.log_line("rpm: %s" % l)
        m = rx.search(l)
        if m: needed[m.group(1)] = 1
    f.close()
    chroot.run("rm -rf %s" % tmpdir)
    if len(needed) == 0:
        b.log_line("no BR needed")
        return
    nbr = ""
    for bre in needed.keys():
        nbr = nbr + " " + re.escape(bre)
    br = string.strip(nbr)
    b.log_line("installing BR: %s" % br)
    res = chroot.run("poldek --up; poldek --upa; poldek --caplookup -Q -v --upgrade %s" % br,
                         user = "root",
                         logfile = b.logfile)
    if res != 0:
        b.log_line("error: BR installation failed")
    return res

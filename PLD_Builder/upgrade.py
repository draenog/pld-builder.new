# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import string
import StringIO

import chroot
import util
import log

hold = [ 
    'poldek',
    'rpm-build'
]

def close_killset(killset):
    k = killset.keys()
    rx = re.compile(r' marks ([^\s]+)-[^-]+-[^-]+$')
    errors = ""
    for p in k:
        if p in hold:
            del killset[p]
            errors += "cannot remove %s because it's crucial\n" % p
        else:
            f = chroot.popen("poldek --noask --test --erase %s" % p, user = "root")
            crucial = 0
            e = []
            for l in f.xreadlines():
                m = rx.search(l)
                if m:
                    pkg = m.group(1)
                    if pkg in hold:
                        errors += "cannot remove %s because it's required " \
                                  "by %s, that is crucial\n" % (p, pkg)
                        crucial = 1
                    e.append(pkg)
            f.close()
            if crucial:
                del killset[p]
            else:
                for p in e:
                    killset[p] = 2
    return errors

def upgrade_from_batch(r, b):
    f = chroot.popen("rpm --test -F %s 2>&1" % string.join(b.files), user = "root")
    killset = {}
    rx = re.compile(r' \(installed\) ([^\s]+)-[^-]+-[^-]+$')
    for l in f.xreadlines():
        m = rx.search(l)
        if m: killset[m.group(1)] = 1
    f.close()
    if len(killset) != 0:
        err = close_killset(killset)
        if err != "":
            util.append_to(b.logfile, err)
            log.notice("cannot upgrade rpms")
            return False
        k = string.join(killset.keys())
        if 0:
            b.log_line("removing %s" % k)
            res = chroot.run("rpm -e %s" % k, logfile = b.logfile, user = "root")
            if res != 0:
                b.log_line("package removal failed")
                return False
        else:
            b.log_line("upgrade would need removal of %s" % k)
            return False
    b.log_line("upgrading packages")
    logbuf = StringIO.StringIO()
    res = chroot.run("rpm -Fvh %s" % string.join(b.files), user = "root", logstdout = logbuf)
    if res != 0:
        b.log_line("package upgrade failed")
        b.log_line(logbuf.getvalue())
        logbuf.close()
        return False
    b.log_line(logbuf.getvalue())
    logbuf.close()
    return True

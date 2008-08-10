# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import string
import StringIO

import chroot
import util
import log

hold = [
    'dev',
    'poldek',
    'rpm-build',
    'pdksh',
    'coreutils'
]

def close_killset(killset):
    k = killset.keys()
    if len(k) == 0:
        return True
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
        if True:
            b.log_line("upgrade requires removal of %s" % k)
            res = chroot.run("rpm -e %s" % k, logfile = b.logfile, user = "root")
            if res != 0:
                b.log_line("package removal failed")
                return False
            else:
                b.log_line("packages removed sucessfuly")
        else:
            b.log_line("upgrade would need removal of %s" % k)
            return False
    b.log_line("upgrading packages")
    logbuf = StringIO.StringIO()
    res = chroot.run("rpm -Fvh %s" % string.join(b.files), user = "root", logfile = b.logfile)
    if res != 0:
        b.log_line("package upgrade failed")
        logbuf.close()
        return False
    logbuf.close()
    return True

def uninstall(conflicting, b):
    b.log_line("uninstalling conflicting packages")
    err = close_killset(conflicting)
    if err != "":
        util.append_to(b.logfile, err)
        b.log_line("error: conflicting packages uninstallation failed")
        return False
    else:
        k = string.join(conflicting.keys())
        b.log_line("removing %s" % k)
        res = chroot.run("poldek --noask --erase %s" % k, logfile = b.logfile, user = "root")
        if res != 0:
            b.log_line("package removal failed")
            return False
    return True

def uninstall_self_conflict(b):
    b.log_line("checking BuildConflict-ing packages")
    rpmbuild_opt = "%s %s %s" % (b.target_string(), b.kernel_string(), b.bconds_string())
    tmpdir = "/tmp/BR." + b.b_id[0:6]
    f = chroot.popen("cd rpm/SPECS; TMPDIR=%s rpmbuild -bp --nobuild --short-circuit --define 'prep exit 0' %s %s 2>&1" \
            % (tmpdir, rpmbuild_opt, b.spec))
    rx = re.compile(r"\s+(\w+)\s+.*\s+conflicts with [^\s]+-[^-]+-[^-]+\.src$")
    conflicting = {}
    for l in f.xreadlines():
        m = rx.search(l)
        if m:
            b.log_line("rpmbuild: %s" % l.rstrip())
            conflicting[m.group(1)] = 1
    f.close()
    if len(conflicting) and not uninstall(conflicting, b):
        return False
    b.log_line("no BuildConflicts found")
    return True

def install_br(r, b):
    # ignore internal rpm dependencies, see lib/rpmns.c for list
    ignore_br = re.compile(r'^\s*(rpmlib|cpuinfo|getconf|uname|soname|user|group|mounted|diskspace|digest|gnupg|macro|envvar|running|sanitycheck|vcheck|signature|verify|exists|executable|readable|writable)\(.*')

    tmpdir = "/tmp/BR." + b.b_id[0:6]
    chroot.run("install -m 700 -d %s" % tmpdir)
    cmd = "cd rpm/SPECS; TMPDIR=%s rpmbuild --nobuild %s %s 2>&1" \
                % (tmpdir, b.bconds_string(), b.spec)
    f = chroot.popen(cmd)
    rx = re.compile(r"^\s*([^\s]+) .*is needed by")
    needed = {}
    b.log_line("checking BR")
    for l in f.xreadlines():
        b.log_line("rpm: %s" % l.rstrip())
        m = rx.search(l)
        if m and not ignore_br.match(l):
            needed[m.group(1)] = 1
    f.close()
    chroot.run("rm -rf %s" % tmpdir)
    if len(needed) == 0:
        b.log_line("no BR needed")
        return True
    nbr = ""
    for bre in needed.keys():
        nbr = nbr + " " + re.escape(bre)
    br = string.strip(nbr)
    b.log_line("updating poldek cache...")
    chroot.run("poldek --up --upa", user = "root", logfile = b.logfile)
    # check conflicts in BRed packages
    b.log_line("checking conflicting packages in BRed packages")
    f = chroot.popen("poldek --test --noask --caplookup -Q -v --upgrade %s" % br, user = "root")
    rx = re.compile(r".*conflicts with installed ([^\s]+)-[^-]+-[^-]+$")
    conflicting = {}
    for l in f.xreadlines():
        b.log_line("poldek: %s" % l.rstrip())
        m = rx.search(l)
        if m: conflicting[m.group(1)] = 1
    f.close()
    if len(conflicting) == 0:
        b.log_line("no conflicts found")
    else:
        if not uninstall(conflicting):
            return False
    b.log_line("installing BR: %s" % br)
    res = chroot.run("poldek --noask --caplookup -Q -v --upgrade %s" % br,
            user = "root",
            logfile = b.logfile)
    if res != 0:
        b.log_line("error: BR installation failed")
        return False
    return True

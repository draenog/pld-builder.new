# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import string
from chroot import *
from util import *

__all__ = ['compute_deps', 'remove_list']

def compute_deps():
    """Compute dependenecies between RPM installed on system.

    Return dictionary from name of package to list of packages required by it.
    Produce some warnings and progress information to stderr.
    """
    # pkg-name -> list of stuff returned by rpm -qR
    rpm_req = {}
    # --whatprovides ...
    rpm_prov = {}
    # list of required files
    req_files = {}
    
    def get_req():
        msg("rpm-req... ")
        f = chr_popen("rpm -qa --qf '@\n%{NAME}\n[%{REQUIRENAME}\n]'")
        cur_pkg = None
        while 1:
            l = f.readline()
            if l == "": break
            l = string.strip(l)
            if l == "@":
                cur_pkg = string.strip(f.readline())
                rpm_req[cur_pkg] = []
                continue
            rpm_req[cur_pkg].append(l)
            if l[0] == '/':
                req_files[l] = 1
        f.close()
        msg("done\n")

    def add_provides(pkg, what):
        if rpm_prov.has_key(what):
            msg("[%s: %s, %s] " % (what, rpm_prov[what], pkg))
        else:
            rpm_prov[what] = pkg
    
    def get_prov():
        msg("rpm-prov... ")
        f = chr_popen("rpm -qa --qf '@\n%{NAME}\n[%{PROVIDENAME}\n]'")
        cur_pkg = None
        while 1:
            l = f.readline()
            if l == "": break
            l = string.strip(l)
            if l == "@":
                cur_pkg = string.strip(f.readline())
                continue
            add_provides(cur_pkg, l)
            if l[0] == '/':
                # already provided
                del req_files[l]
        f.close()
        msg("done\n")
 
    def get_prov_files():
        msg("rpm-files... ")
        f = chr_popen("rpm -qa --qf '@\n%{NAME}\n[%{FILENAMES}\n]'")
        cur_pkg = None
        while 1:
            l = f.readline()
            if l == "": break
            l = string.strip(l)
            if l == "@":
                cur_pkg = string.strip(f.readline())
                continue
            if req_files.has_key(l):
                add_provides(cur_pkg, l)
        f.close()
        msg("done\n")

    def compute():
        msg("computing deps... ")
        for pkg, reqs in rpm_req.items():
            pkg_reqs = []
            for req in reqs:
                if req[0:7] == "rpmlib(": continue
                if rpm_prov.has_key(req):
                    if rpm_prov[req] not in pkg_reqs:
                        pkg_reqs.append(rpm_prov[req])
                else:
                    msg("[%s: %s] " % (pkg, req))
            requires[pkg] = pkg_reqs
        msg("done\n")
        
    # map from pkg-name to list of pkg-names required by it
    # this is result
    requires = {}

    get_req()
    get_prov()
    get_prov_files()
    compute()
    return requires

def remove_list(req, need):
    """List of packages scheduled for removal.
    
    Given dependency information and list of needed packages compute list
    of packages that don't need to be present.
    """
    need_m = {}
    def close(n):
        if need_m.has_key(n): return
        need_m[n] = 1
        if not req.has_key(n): return
        for k in req[n]:
            close(k)
    for n in need: close(n)
    rm = []
    for p in req.keys():
        if not need_m.has_key(p): rm.append(p)
    return rm

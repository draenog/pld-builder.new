# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import types
import string
import xreadlines

from chroot import *
from util import *


def get_poldek_requires():
    # precompile regexps
    name_rx = re.compile(r"\d+\. ([^\s]+)-[^-]+-[^-]+\n")
    req_rx = re.compile(r" req .* --> (.*)\n")
    pkg_name_rx = re.compile(r"([^\s]+)-[^-]+-[^-]+")

    # todo: if a and b are sets, then use sets module
    # and intersection method on set object
    def intersect(a, b):
        r = []
        for x in a:
            if x in b: r.append(x)
        return r

    # add given req-list to cur_pkg_reqs
    def add_req(reqs):
        if len(reqs) == 1:
            if reqs[0] not in cur_pkg_reqs:
                cur_pkg_reqs.append(reqs[0])
        else:
            did = 0
            for x in cur_pkg_reqs:
                if type(x) is types.ListType:
                    i = intersect(x, reqs)
                    if len(i) == 0:
                        continue
                    did = 1
                    idx = cur_pkg_reqs.index(x)
                    if len(i) == 1:
                        if i[0] in cur_pkg_reqs:
                            del cur_pkg_reqs[idx]
                        else:
                            cur_pkg_reqs[idx] = i[0]
                    else:
                        cur_pkg_reqs[idx] = i
                else:
                    if x in reqs:
                        return
            if not did:
                cur_pkg_reqs.append(reqs)

    pkg_reqs = {}
    cur_pkg_reqs = None
    cur_pkg = None

    f = chr_popen("poldek -v -v --verify --unique-pkg-names")
    for l in xreadlines.xreadlines(f):
        m = name_rx.match(l)
        if m:
            if cur_pkg:
                pkg_reqs[cur_pkg] = cur_pkg_reqs
            cur_pkg = m.groups(1)
            if pkg_reqs.has_key(cur_pkg):
                cur_pkg = None
                cur_pkg_reqs = None
            else:
                cur_pkg_reqs = []
            continue
        m = req_rx.match(l)
        if m:
            reqs = []
            for x in string.split(m.group(1)):
                if x in ["RPMLIB_CAP", "NOT", "FOUND", "UNMATCHED"]: continue
                m = pkg_name_rx.match(x)
                if m:
                    reqs.append(m.group(1))
                else:
                    msg("poldek_reqs: bad pkg name: %s\n" % x)
            if len(reqs) != 0: add_req(reqs)

    f.close()

    if cur_pkg:
        pkg_reqs[cur_pkg] = cur_pkg_reqs

    return pkg_reqs

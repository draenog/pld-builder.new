# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import re
import md5
import random

from config import config

def quote(cmd):
    return re.sub("([\"\\\\$`])", r"\\\1", cmd)
    
def command(cmd, user = None):
    if user == None:
        user = config.builder_user
    return "%s sudo chroot %s su - %s -c \"export LC_ALL=C; %s\"" \
            % (config.sudo_chroot_wrapper, config.chroot, user, quote(cmd))
    
def command_sh(cmd):
    return "%s sudo chroot %s /bin/sh -c \"export LC_ALL=C; %s\"" \
            % (config.sudo_chroot_wrapper, config.chroot, quote(cmd))

def popen(cmd, user = "builder", mode = "r"):
    f = os.popen(command(cmd, user), mode)
    return f
    
def run(cmd, user = "builder", logfile = None, logstdout = None):
    c = command(cmd, user)
    if logfile != None:
        if logstdout != None:
            c = "%s 2>&1 | /usr/bin/tee -a %s" % (c, logfile)
        else:
            c = "%s >> %s 2>&1" % (c, logfile)
    f = os.popen(c)
    for l in f:
        if logstdout != None:
            logstdout.write(l)
    r = f.close()
    if r == None:
        return 0
    else:
        return r

def cp(file, outfile, user="builder", rm=False):
    m = md5.new()
    m.update(str(random.getrandbits(4096)))
    digest = m.hexdigest()

    marker_start = "--- FILE BEGIN DIGEST %s ---" % digest
    marker_end = "--- FILE END DIGEST %s ---" % digest

    f = open(outfile, 'w')
    cmd = "echo \"%s\"; cat %s; echo \"%s\"" % (marker_start, file, marker_end)
    if rm:
        cmd += "; rm %s" % file
    c = command(cmd, user)
    p = os.popen(c)
    # get file contents
    marker = False
    for l in p:
        if not marker and l.strip() == marker_start:
            marker = True
            continue
        me = l.strip().find(marker_end)
        if me != -1:
            l = l[:me]
            f.write(l)
            marker = False
            break
        if marker:
            f.write(l)
    rp = p.close()
    rf = f.close()
    if rp == None:
        return 0
    else:
        return r

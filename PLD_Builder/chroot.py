# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import re
import subprocess
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

def cp(file, outfile, rm=False):
    f = open(outfile, 'w')
    fileno = f.fileno()
    cmd = "cat %s >&%d" % (file, fileno)
    if rm:
        cmd += "; rm %s" % file
    c = command_sh(cmd)
    subprocess.call(c, shell = True, close_fds = False)
    r = f.close()
    if r == None:
        return 0
    else:
        return r

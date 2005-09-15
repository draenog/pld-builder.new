# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import re
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
    
def run(cmd, user = "builder", logfile = None, logstdout = False):
    c = command(cmd, user)
    if logfile != None:
        if logstdout:
            c = "%s 2>&1 | tee %s" % (c, logfile)
        else:
            c = "%s >> %s 2>&1" % (c, logfile)
    lines = ""
    f = os.popen(c)
    for l in f:
        lines += l
    r = f.close()
    if r == None:
        if logstdout:
            return lines
        else:
            return 0
    else:
        return r

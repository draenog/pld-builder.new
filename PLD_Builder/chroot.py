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
  
def run(cmd, user = "builder", logfile = None):
  c = command(cmd, user)
  if logfile != None:
    # c = "%s >> %s 2>&1" % (c, logfile)
    c = c+" >> "+logfile+" 2>&1"  
  f = os.popen(c)
  for l in f.xreadlines():
    pass
  r = f.close()
  if r == None:
    return 0
  else:
    return r

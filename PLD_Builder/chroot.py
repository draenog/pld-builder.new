import os
import re
from config import config

def quote(cmd):
  return re.sub("([\"\\\\$`])", r"\\\1", cmd)
  
def command(cmd, user = "builder"):
  return "sudo chroot %s su - %s -c \"export LC_ALL=C; %s\"" % (config.chroot, user, quote(cmd))
  
def command_sh(cmd):
  return "sudo chroot %s /bin/sh -c \"export LC_ALL=C; %s\"" % (config.chroot, quote(cmd))

def popen(cmd, user = None):
  f = os.popen(command(cmd, user))
  return f
  
def run(cmd, user = None, logfile = None)
  c = command(cmd, user)
  if logfile != None:
    c = "%s >> %s 2>&1" % (c, logfile)
  f = os.popen(c)
  for l in f.xreadlines():
    pass
  r = f.close()
  if r == None:
    return 0
  else
    return r
    
locale.sanitize()

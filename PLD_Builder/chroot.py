import os

def chr_cmd(cmd):
  return "sudo chroot /adm/chroot-i386 /bin/sh -c \"%s\"" % cmd
  #return cmd
  
def chr_popen(cmd):
  f = os.popen(chr_cmd(cmd))
  return f

def chr_system(cmd):
  os.system(chr_cmd(cmd))

# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

from config import config, init_conf
import path
import os
import time
import util
import chroot

def clean_dir(path, max):
    curtime=time.time()
    for i in os.listdir(path):
        if curtime - os.path.getmtime(path+'/'+i) > max:
            if os.path.isdir(path+'/'+i):
                util.clean_tmp(path+'/'+i)
            else:
                os.unlink(path+'/'+i)

def handle_src():
    clean_dir(path.www_dir+'srpms', 2592000) # a month

def handle_bin():
    f=chroot.popen("""ls -l --time-style +%s /spools/ready""", 'root')
    rmpkgs=[]
    curtime=time.time()
    for i in f:
        if i[-4:-1]!='rpm':
            continue
        tmp=i.split()
        mtime=int(tmp[5])
        pkgname=tmp[6]
        if curtime - mtime > config.max_keep_time:
            rmpkgs.append(pkgname)
    if rmpkgs:
        chroot.run("cd /spools/ready; rm %s" % ' '.join(rmpkgs))
    f.close()

if __name__ == '__main__':
    init_conf()
    bb=config.binary_builders[:]
    clean_dir(path.spool_dir+'builds', 2592000) # a month
    if config.src_builder:
        try:
            init_conf(config.src_builder)
        except:
            pass
        else:
            handle_src()
    for b in bb:
        try:
            init_conf(b)
        except:
            continue
        else:
            handle_bin()


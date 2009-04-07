# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import sys
import time
import datetime

from config import config, init_conf
import util
import chroot
import ftp
import path

def clean_dir(path, max):
    curtime=time.time()
    for i in os.listdir(path):
        if curtime - os.path.getmtime(path+'/'+i) > max:
            if os.path.isdir(path+'/'+i):
                util.clean_tmp(path+'/'+i)
            else:
                os.unlink(path+'/'+i)

def send_rpmqa():
    tmp = path.build_dir + '/' + util.uuid() + '/'
    os.mkdir(tmp)
    log = tmp + config.rpmqa_filename
    open(log, 'a').write("Query done at: %s\n" % datetime.datetime.now().isoformat(' '))
    chroot.run("rpm -qa|sort", logfile=log)
    os.chmod(log,0644)
    ftp.init(rpmqa=True)
    ftp.add(log)
    ftp.flush()
    os.unlink(log)
    os.rmdir(tmp)

def handle_src():
    send_rpmqa()
    clean_dir(path.www_dir+'/srpms', 2592000) # a month

def handle_bin():
    send_rpmqa()
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

    i=0
    while rmpkgs[i:i+1000]:
        chroot.run("cd /spools/ready; rm -f %s" % ' '.join(rmpkgs[i:i+1000]), 'root')
        i=i+1000
    f.close()
    chroot.run("poldek --mo=nodiff --mkidxz -s /spools/ready")

if __name__ == '__main__':
    init_conf()
    bb=config.binary_builders[:]
    clean_dir(path.spool_dir+'/builds', 2592000) # a month
    if config.src_builder:
        try:
            init_conf(config.src_builder)
        except:
            pass
        else:
            handle_src()
            sys.exit(0)
    for b in bb:
        try:
            init_conf(b)
        except:
            continue
        else:
            handle_bin()


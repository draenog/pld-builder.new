# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

from config import config, init_conf
import path
import os
import time
import util

def clean_dir(path, max):
    curtime=time.time()
    for i in os.listdir(path):
        if curtime - os.path.getmtime(path+'/'+i) > max:
            if os.path.isdir(path+'/'+i):
                print "rmdir: %s" % path+'/'+i
            else:
                print "rmfile: %s" % path+'/'+i

def handle_src():
    clean_dir(path.www_dir+'srpms', 2592000) # a month

def handle_bin():
    pass

if __name__ == '__main__':
    init_conf()
    bb=config.binary_builders[:]
    clean_dir(path.spool_dir+'builds', config.max_keep_time)
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


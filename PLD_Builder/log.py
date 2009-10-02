# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import sys
import time
import syslog

import path

builder = ""
do_syslog = 0

# string containing last log entry,
# as the code is flawed to get this otherwise
_last_log = ""

def log(p, s):
    global _last_log
    _last_log = s

    if do_syslog:
        try:
            syslog.syslog(p, str(s))
        except TypeError:
            syslog.syslog(p, repr(s))
    f = open(path.log_file, "a")
    f.write("%s [%s]: %s [%s]\n" % (time.asctime(), builder, s, os.path.basename(sys.argv[0])))
    f.close()
    
def panic(s):
    log(syslog.LOG_ALERT, "PANIC: %s" % s)
    raise Exception, "PANIC: %s" % str(s)

def alert(s):
    log(syslog.LOG_ALERT, "alert: %s" % s) 
 
def error(s):
    log(syslog.LOG_ERR, "error: %s" % s) 
 
def warn(s):
    log(syslog.LOG_WARNING, "warning: %s" % s) 
 
def notice(s):
    log(syslog.LOG_NOTICE, "notice: %s" % s) 

def open_syslog(name, f):
    global do_syslog
    do_syslog = 1
    syslog.openlog(name, syslog.LOG_PID, f)

def last_log():
    return _last_log

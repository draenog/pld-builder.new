# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import path
import time
import os
import re
import log

from config import config
import util

class Buildlogs_Queue:
    def __init__(self):
        self.queue = []
        self.some_failed = 0
        self.requester_email = None

    def init(self, g):
        self.requester_email = g.requester_email

    def add(self, logfile, failed, id):
        # if /dev/null, don't even bother to store it
        if config.buildlogs_url == "/dev/null":
            return
        blogfile = os.path.basename(logfile)
        name = re.sub(r"\.spec\.log", "", blogfile) + "," + id + '.' + blogfile + ".bz2"
        ret = os.system("bzip2 --best --force < %s > %s" \
                    % (logfile, path.buildlogs_queue_dir + '/' + id '.' + blogfile))
        if ret:
            log.error("bzip2 compression of %s failed; does bzip2 binary exist?" % (logfile))

        if failed: s = "FAIL"
        else: s = "OK"
        f = open(path.buildlogs_queue_dir + '/' + id + '.' + blogfile + ".info", "w")
        f.write("Status: %s\nEND\n" % s)
        f.close()

        self.queue.append({'name': name, 'id': id + '.' + blogfile, 'failed': failed})

    def flush(self):
        def desc(l):
            return """Target: %s/%s
Builder: %s
Time: %d
Type: buildlog
Requester: %s
END
""" % (config.buildlogs_url, l['name'], config.builder, time.time(), self.requester_email)
        
        for l in self.queue:
            f = open(path.buildlogs_queue_dir + '/' + l['id'] + ".desc.tmp", "w")
            f.write(desc(l))
            f.close()
            os.rename(path.buildlogs_queue_dir + '/' + l['id'] + ".desc.tmp", path.buildlogs_queue_dir + '/' + l['id'] + ".desc")

queue = Buildlogs_Queue()

def init(r):
    queue.init(r)

def add(logfile, failed, id):
    "Add new buildlog with specified status."
    queue.add(logfile, failed, id)

def flush():
    "Send buildlogs to server."
    queue.flush()

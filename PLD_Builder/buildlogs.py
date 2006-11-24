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

    def init(self, g):
        self.requester_email = g.requester_email

    def add(self, logfile, failed):
        # if /dev/null, don't even bother to store it
        if config.buildlogs_url == "/dev/null":
            return
        name = re.sub(r"\.spec\.log", "", os.path.basename(logfile)) + ".bz2"
        id = util.uuid()
        ret = os.system("bzip2 --best --force < %s > %s" \
                    % (logfile, path.buildlogs_queue_dir + id))
        if ret:
            log.error("bzip2 compression of %s failed; does bzip2 binary exist?" % (logfile))

        if failed: s = "FAIL"
        else: s = "OK"
        f = open(path.buildlogs_queue_dir + id + ".info", "w")
        f.write("Status: %s\nEND\n" % s)
        f.close()

        self.queue.append({'name': name, 'id': id, 'failed': failed})

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
            f = open(path.buildlogs_queue_dir + l['id'] + ".desc", "w")
            f.write(desc(l))
            f.close()

queue = Buildlogs_Queue()

def init(r):
    queue.init(r)

def add(logfile, failed):
    "Add new buildlog with specified status."
    queue.add(logfile, failed)

def flush():
    "Send buildlogs to server."
    queue.flush()

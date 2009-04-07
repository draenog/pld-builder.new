# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import path
import os
import shutil
import time

from config import config
import util

class Notify_Queue:
    def __init__(self):
        self.queue = None
        self.some_failed = 0

    def init(self, g=None):
        self.queue = []
        self.requester_email = g.requester_email
        self.notify_url = config.notify_url
        
    def add(self, file):
        id = util.uuid()
        f = open(path.notify_queue_dir + '/' + id, 'w')
        f.write(file.read())
        f.close()
        self.queue.append({'id': id})

    def flush(self):
        def desc(l):
            return """Target: %s
Id: %s
Builder: %s
Time: %d
Requester: %s
END
""" % (self.notify_url, l['id'], config.builder, time.time(), self.requester_email)
        
        for l in self.queue:
            f = open(path.notify_queue_dir + '/' + l['id'] + ".desc", "w")
            f.write(desc(l))
            f.close()

    def kill(self):
        for l in self.queue:
            os.unlink(path.notify_queue_dir + '/' + l)

queue = Notify_Queue()

def add(notify):
    queue.add(notify)

def flush():
    queue.flush()
    
def kill():
    queue.kill()

def init(r):
    queue.init(r)

def status():
    return queue.status
    
def clear_status():
    queue.status = ""

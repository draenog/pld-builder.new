import path
import time
import os

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
    name = os.path.basename(logfile) + ".bz2"
    id = util.uuid()
    os.system("bzip2 --best --force < %s > %s" \
                % (logfile, path.buildlogs_queue_dir + id))

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

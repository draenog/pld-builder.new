import path
import os

from config import config

class Buildlogs_Queue:
  def __init__(self):
    self.queue = []
    self.some_failed = 0

  def add(self, logfile, failed):
    name = os.path.basename(logfile) + ".bz2"
    os.system("bzip2 --best --force < %s > %s" \
                % (logfile, path.buildlogs_queue_dir + name))
    self.queue.append({'name': name, 'failed': failed})

  def flush(self):
    def desc(l):
      if l['failed']: s = "FAIL"
      elif self.some_failed: s = "OKOF" # OK but Others Failed
      else: s = "OK"
      return "Target: %s/%s\nBuilder: %s\nStatus: %s\nEND\n" % \
                (config.buildlogs_url, l['name'], config.builder, s)
    
    for l in self.queue:
      f = open(path.buildlogs_queue_dir + l['name'] + ".desc", "w")
      f.write(desc(l))
      f.close()

queue = Buildlogs_Queue()

def add(logfile, failed):
  "Add new buildlog with specified status."
  queue.add(logfile, failed)

def flush():
  "Send buildlogs to server."
  queue.flush()

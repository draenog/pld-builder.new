import path
import os
import shutil

from config import config
import util

class FTP_Queue:
  def __init__(self):
    self.queue = []
    self.some_failed = 0

  def add(self, file):
    # if /dev/null, say bye bye
    if config.ftp_url == "/dev/null":
      return
    name = os.path.basename(file)
    id = util.uuid()
    shutil.copy(file, path.ftp_queue_dir + id)
    self.queue.append({'name': name, 'id': id})

  def flush(self):
    def desc(l):
      return "Target: %s/%s\nBuilder: %s\nEND\n" % \
                (config.ftp_url, l['name'], config.builder)
    
    for l in self.queue:
      f = open(path.ftp_queue_dir + l['id'] + ".desc", "w")
      f.write(desc(l))
      f.close()

  def kill(self):
    for l in self.queue:
      os.unlink(path.ftp_queue_dir + l)

queue = FTP_Queue()

def add(f):
  queue.add(f)

def flush():
  queue.flush()
  
def kill():
  queue.kill()

import path
import os
import shutil
import time

from config import config
import util
from acl import acl

class FTP_Queue:
  def __init__(self):
    self.queue = None
    self.some_failed = 0
    self.status = ""

  def init(self, g):
    self.queue = []
    if "test-build" in g.flags:
      self.url = config.test_ftp_url
    else:
      self.url = config.ftp_url
    
  def add(self, file):
    # if /dev/null, say bye bye
    if self.url == "/dev/null":
      return
    name = os.path.basename(file)
    id = util.uuid()
    shutil.copy(file, path.ftp_queue_dir + id)
    self.queue.append({'name': name, 'id': id})
    st = os.stat(path.ftp_queue_dir + id)
    self.status += "%10d %s\n" % (st.st_size, name)

  def flush(self):
    def desc(l):
      return "Target: %s/%s\nBuilder: %s\nTime: %d\nRequester: %s\nEND\n" % \
                (self.url, l['name'], config.builder, time.time(), 
                 acl.current_user_login())
    
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

def init(r):
  queue.init(r)

def status():
  return queue.status
  
def clear_status():
  queue.status = ""

import re
import gzip
import time
import StringIO
import os
import fcntl

# PLD_Builder:
import gpg
import request


class B_Queue:
  def __init__(self, filename):
    self.name = filename
    self.requests = []
    self.fd = None
  
  # read possibly compressed, signed queue
  def read_signed(self):
    if re.search(r"\.gz$", self.name):
      f = gzip.open(self.name)
    else:
      f = open(self.name)
    (signers, body) = gpg.verify_sig(f)
    self.signers = signers
    self.requests = request.parse_requests(body)

  def _open(self):
    if self.fd == None:
      if os.access(self.name, os.F_OK):
        self.fd = open(self.name, "r+")
      else:
        self.fd = open(self.name, "w+")
    
  def read(self):
    self._open()
    self.signers = []
    self.requests = request.parse_requests(self.fd)

  def _write_to(self, f):
    f.write("<queue>\n")
    for r in self.requests:
      r.write_to(f)
    f.write("</queue>\n")

  def write(self):
    self._open()
    self.fd.seek(0)
    self.fd.truncate(0)
    self._write_to(self.fd)

  def lock(self, no_block):
    self._open()
    op = fcntl.LOCK_EX
    if no_block:
      op = op + fcntl.LOCK_NB
    try:
      fcntl.flock(self.fd, op)
      return 1
    except IOError:
      return 0
  
  def unlock(self):
    fcntl.flock(self.fd, fcntl.LOCK_UN)

  def write_signed(self, name):
    sio = StringIO.StringIO()
    self._write_to(sio)
    sio.seek(0)
    sio = gpg.sign(sio)
    if os.access(name, os.F_OK): os.unlink(name)
    if re.search(r"\.gz$", name):
      f = gzip.open(self.name, "w", 6)
    else:
      f = open(self.name, "w")
    f.write(sio.read())
    f.close()

  def add(self, req):
    self.requests.append(req)

  def value(self):
    return self.requests
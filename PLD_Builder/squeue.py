# Queue on src-builder

import re
import gzip
import time
import StringIO

# PLD_Builder:
import gpg
import request

class Src_Queue:
  def __init__(self, filename):
    self.name = filename
    self.requests = []
    self.is_gzip = 0
    
  def read(self):
    if re.search(r"\.gz$", self.name):
      f = gzip.open(self.name)
      self.is_gzip = 1
    else:
      f = open(self.name)
      self.is_gzip = 0
    (signers, body) = gpg.verify_sig(f)
    # maybe check signers here?
    self.requests = request.parse_requests(body)

  def write(self):
    sio = StringIO.StringIO()
    sio.write("<queue>\n")
    for r in self.requests:
      r.write_to(sio)
    sio.write("</queue>\n")
    sio.seek(0)
    sio = gpg.sign(sio)
    if self.is_gzip:
      f = gzip.open(self.name, "w", 6)
    else:
      f = open(self.name, "w")
    f.write(sio.read())
    f.close()

  def remove_old(self):
    now = time.time()
    def is_old(r): return now - r.time > 30 * 24 * 3600
    self.requests = filter(is_old, self.requests)

  def add(self, req):
    self.requests.append(req)

  def value():
    return self.requests

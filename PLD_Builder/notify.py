import StringIO

import mailer
import gpg
from config import config

class Notifier:
  def __init__(self, g):
    self.xml = StringIO.StringIO()
    self.xml.write("<notification group-id='%s' builder='%s'>\n" % \
                        (g.id, config.builder))
  
  def send(self):
    self.xml.write("</notification>\n")
    msg = mailer.Message()
    msg.set_headers(to = config.notify_email, subject = "status notification")
    msg.write(gpg.sign(self.xml))
    msg.send()
    self.xml = None
  
  def add_batch(self, b, s):
    self.xml.write("  <batch id='%s' status='%s'>\n" % (b.b_id, s))
  
n = None

def begin(group):
  global n
  n = Notifier(group)

def add_batch(batch, status):
  n.add_batch(batch, status)

def send():
  n.send()

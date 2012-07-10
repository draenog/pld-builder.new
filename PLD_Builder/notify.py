# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import StringIO

import mailer
import gpg
import util
import notifyq
from config import config

class Notifier:
    def __init__(self, g):
        self.xml = StringIO.StringIO()
        self.xml.write("<notification group-id='%s' builder='%s'>\n" % \
                        (g.id, config.builder))

    def send(self, r):
        sio = StringIO.StringIO()
        self.xml.write("</notification>\n")
        self.xml.seek(0)
        sio.write(gpg.sign(self.xml.read()))
        self.xml = None
        sio.seek(0)
        notifyq.init(r)
        notifyq.add(sio)
        notifyq.flush()

    def add_batch(self, b, s):
        self.xml.write("  <batch id='%s' status='%s' />\n" % (b.b_id, s))

n = None

def begin(group):
    global n
    n = Notifier(group)

def add_batch(batch, status):
    n.add_batch(batch, status)

def send(r):
    n.send(r)

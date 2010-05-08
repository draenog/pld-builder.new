# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import re
import gzip
import time
import StringIO
import os
import fcntl
import string

# PLD_Builder:
import gpg
import request
import util
import log

class B_Queue:
    def __init__(self, filename):
        self.name = filename
        self.requests = []
        self.fd = None

    def dump(self, f):
        self.requests.reverse()
        for r in self.requests:
            r.dump(f)
        self.requests.reverse()
    
    def dump_html(self, f):
        f.write("""
<html>
    <head>
    <link rel="Shortcut Icon" href="http://www.pld-linux.org/favicon.ico"/>
        <title>PLD builder queue</title>
        <link rel="stylesheet" type="text/css" charset="utf-8" media="all" href="style.css">
    </head>
<body>\n"""
        )
        self.requests.reverse()
        for r in self.requests:
            r.dump_html(f)
        self.requests.reverse()
        f.write("</body></html>\n")
    
    # read possibly compressed, signed queue
    def read_signed(self):
        if re.search(r"\.gz$", self.name):
            f = gzip.open(self.name)
        else:
            f = open(self.name)
        (signers, body) = gpg.verify_sig(f.read())
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
        body = self.fd.read()
        if string.strip(body) == "":
            # empty file, don't choke
            self.requests = []
            return
        try:
            self.requests = request.parse_requests(body)
        except Exception, e:
            log.panic("error parsing %s: %s" % (self.name, e))
            pass

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
        self.fd.flush()

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
        sio.write(gpg.sign(sio.read()))
        if os.access(name, os.F_OK): os.unlink(name)
        if re.search(r"\.gz$", name):
            f = gzip.open(name, "w", 6)
        else:
            f = open(name, "w")
        sio.seek(0)
        util.sendfile(sio, f)
        f.close()

    def add(self, req):
        self.requests.append(req)

    def value(self):
        return self.requests

# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import time
import os
import sys
import StringIO

from config import config
import util
import log

def recode(s):
    if s.__class__ == ''.__class__:
        return s.decode('iso-8859-1', 'replace').encode('us-ascii', 'replace')
    else:
        return s.encode('us-ascii', 'replace')

class Message:
    def __init__(self):
        self.headers = {}
        self.body = StringIO.StringIO()
        self.set_std_headers()

    def set_header(self, n, v):
        self.headers[n] = v

    def set_headers(self, to = None, cc = None, subject = None):
        if to != None:
            self.set_header("To", to)
        if cc != None:
            self.set_header("Cc", cc)
        if subject != None:
            self.set_header("Subject", subject)

    def write_line(self, l):
        self.body.write(recode("%s\n" % l))

    def write(self, s):
        self.body.write(recode(s))

    def append_log(self, log):
        s = os.stat(log)
        if s.st_size > 50000:
            # just head and tail
            f = open(log)
            line_cnt = 0
            for l in f.xreadlines():
                line_cnt += 1
            f.seek(0)
            line = 0
            for l in f.xreadlines():
                if line < 100 or line > line_cnt - 100:
                    self.body.write(recode(l))
                if line == line_cnt - 100:
                    self.body.write("\n\n[...]\n\n")
                line += 1
        else:
            util.sendfile(open(log), self.body)

    def set_std_headers(self):
        self.headers["Date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        self.headers["Message-ID"] = "<pld-builder.%f.%d@%s>" \
                % (time.time(), os.getpid(), os.uname()[1])
        self.headers["From"] = "PLD %s builder <%s>" \
                % (config.builder, config.email)
        self.headers["X-PLD-Builder"] = config.builder

    def write_to(self, f):
        for k, v in self.headers.items():
            f.write("%s: %s\n" % (k, v))
        f.write("\n")
        self.body.seek(0)
        util.sendfile(self.body, f)

    def send(self):
        if not os.path.exists("/usr/lib/sendmail"):
            # TODO: dump to file?
            log.alert("/usr/lib/sendmail doesn't exist: Can't send email")
            return False
        send_sendmail = "/usr/lib/sendmail -i -t -f %s" % config.admin_email
        f = os.popen(send_sendmail, "w")
        try:
            self.write_to(f)
        except IOError, e:
            log.alert("sending email message failed: %s" % e)
            f.close()
            return False
        return f.close()

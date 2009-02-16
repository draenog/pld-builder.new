# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import sys
import log
import traceback
import StringIO
import os
import time

# this module, as it deals with internal error handling shouldn't
# import anything beside status
import status

try:
    import mailer
    def sendmail(trace):
        m = mailer.Message()
        m.set_headers(to = status.admin, cc = "%s, %s" % (status.email, status.builder_list), subject = "fatal python exception")
        m.write("%s\n" % trace)
        m.write("during: %s\n" % status.get())
        m.send()
except:
    def sendmail(trace):
        # don't use mailer.py; it safer this way
        f = os.popen("/usr/sbin/sendmail -i -t", "w")
        f.write("""Subject: builder failure
To: %s
Cc: %s, %s
Date: %s
X-PLD-Builder: fatal error report

%s

during: %s
""" % (status.admin, status.email, status.builder_list,
             time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
             trace, status))
        f.close()

def wrap(main):
    try:
        main()
    except:
        exctype, value = sys.exc_info()[:2]
        if exctype == SystemExit:
            sys.exit(value)
        s = StringIO.StringIO()
        traceback.print_exc(file = s, limit = 20)

        log.alert("fatal python exception")
        log.alert(s.getvalue())
        log.alert("during: %s" % status.get())

        sendmail(s.getvalue())

        sys.exit(1)

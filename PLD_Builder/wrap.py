import sys
import log
import traceback
import StringIO
import os
import time

# this module, as it deals with internal error handling shouldn't
# import anything beside status

import status

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
    
    # don't use mailer.py; it safer this way
    f = os.popen("/usr/sbin/sendmail -t", "w")
    f.write("""Subject: builder failure
To: %s
Cc: %s
Date: %s
X-PLD-Builder: fatal error report

%s

during: %s
""" % (status.admin, status.email, time.asctime(), s.getvalue(), status.get()))
    f.close()

    sys.exit(1)

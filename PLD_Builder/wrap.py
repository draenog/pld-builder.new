import sys
import log
import traceback
import StringIO

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
    log.alert("fatal python exception during: %s" % status.get())
    log.alert(s.getvalue())
    sys.exit(1)

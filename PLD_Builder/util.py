import re
import sys
import os
import log
import traceback
import StringIO

def pkg_name(nvr):
  return re.match(r"(.+)-[^-]+-[^-]+", nvr).group(1)
  
def msg(m):
  sys.stderr.write(m)

def sendfile(src, dst):
  while 1:
    s = src.read(10000)
    if s == "": break
    dst.write(s)

def append_to(log, msg):
  f = open(log, "a")
  f.write("%s\n" % msg)
  f.close()

def clean_tmp(dir):
  # FIXME: use python
  os.system("rm -f %s/* 2>/dev/null; rmdir %s 2>/dev/null" % (dir, dir))

status = "unknown"

def wrap(main):
  try:
    main()
  except:
    exctype, value = sys.exc_info()[:2]
    if exctype == SystemExit:
      sys.exit(value)
    s = StringIO.StringIO()
    traceback.print_exc(file = s, limit = 20)
    log.alert("fatal python exception during: %s" % status)
    log.alert(s.getvalue())
    sys.exit(1)

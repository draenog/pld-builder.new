import re
import sys

def pkg_name(nvr):
  return re.match(r"(.+)-[^-]+-[^-]+", nvr).group(1)
  
def msg(m):
  sys.stderr.write(m)

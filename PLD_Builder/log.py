import sys

def log(s):
  sys.stderr.write("LOG: %s\n" % s)
  
def alert(s):
  log("alert: %s" % s) 
 
def error(s):
  log("error: %s" % s) 
 
def warn(s):
  log("warning: %s" % s) 
 
def notice(s):
  log("notice: %s" % s) 

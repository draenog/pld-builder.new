import sys

builder = ""

def log(s):
  sys.stderr.write("LOG[%s]: %s\n" % (builder, s))
  
def alert(s):
  log("alert: %s" % s) 
 
def error(s):
  log("error: %s" % s) 
 
def warn(s):
  log("warning: %s" % s) 
 
def notice(s):
  log("notice: %s" % s) 

def panic(s):
  log("PANIC: %s" % s)
  raise "PANIC: %s" % s

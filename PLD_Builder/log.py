import sys
import time

import path

builder = ""

def log(s):
  f = open(path.log_file, "a")
  f.stderr.write("%s [%s]: %s\n" % (time.asctime(), builder, s))
  f.close()
  
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

import fcntl

import path

def lock(n):
  f = open(path.lock_dir + n, "w")
  fcntl.flock(f, fcntl.LOCK_EX)
  return f

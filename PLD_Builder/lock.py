import fcntl

import path

def lock(n, non_block = 0):
  f = open(path.lock_dir + n, "w")
  if non_block:
    try:
      fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except:
      f.close()
      return None
  else:
    fcntl.flock(f, fcntl.LOCK_EX)
  return f

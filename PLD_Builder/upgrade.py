import re
import string

import chroot

hold = [ 
  'poldek',
  'rpm-build'
]

def close_killset(killset):
  k = killset.keys()
  rx = re.compile(r' marks ([^\s]+)-[^-]+-[^-]+$')
  errors = ""
  for p in k:
    if p in hold:
      del killset[p]
      errors += "cannot remove %s because it's crucial\n" % p
    else:
      f = chroot.popen("poldek --noask --test --erase %s" % p, user = "root")
      crucial = 0
      e = []
      for l in f.xreadlines():
        m = rx.search(l)
        if m:
          pkg = m.group(1)
          if pkg in hold:
            errors += "cannot remove %s because it's required by %s, that is crucial\n" % \
                        (p, pkg)
            crucial = 1
          e.append(pkg)
      f.close()
      if crucial:
        del killset[p]
      else:
        for p in e:
          killset[p] = 2
  return errors

def upgrade_from_batch(r, b):
  f = chroot.popen("rpm --test -F %s 2>&1" % string.join(b.files), user = "root")
  killset = {}
  rx = re.compile(r' ([^\s]+)-[^-]+-[^-]+$')
  for l in f.xreadlines():
    m = rx.search(l)
    if m: killset[m.group(1)] = 1
  f.close()
  if len(killset) != 0:
    err = close_killset(killset)
    if err != "":
      util.append_to(b.logfile, err)
      log.notice("cannot upgrade rpms")
      return
    k = string.join(killset.keys())
    b.log_line("removing %s")
    res = chroot.run("rpm -e %s" % k, logfile = b.logfile, user = "root")
    if res != 0:
      b.log_line("package removal failed")
      return
  b.log_line("upgrading packages")
  res = chroot.run("rpm --test -Fvh %s" % string.join(b.files), user = "root")
  if res != 0:
    b.log_line("package upgrade failed")
    return

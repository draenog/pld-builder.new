import re
import string

import chroot

def install_br(r, b):
  cmd = "cd rpm/SPECS; TMPDIR=$HOME/%s rpmbuild --nobuild %s %s 2>&1" \
        % (b.b_id, b.bconds_string(), b.spec)
  f = chroot.popen(cmd)
  rx = re.compile(r"^\s*([^\s]+) .*is needed by")
  needed = {}
  b.log_line("checking BR")
  for l in f.xreadlines():
    b.log_line("rpm: %s" % l)
    m = rx.search(l)
    if m: needed[m.group(1)] = 1
  f.close()
  if len(needed) == 0:
    b.log_line("no BR needed")
    return
  br = string.join(needed.keys())
  b.log_line("installing BR: %s" % br)
  res = chroot.run("poldek --up; poldek --upa; poldek --unique-pkg-names -v --upgrade %s" % br,
             user = "root",
             logfile = b.logfile)
  if res != 0:
    b.log_line("error: BR installation failed")
  return res

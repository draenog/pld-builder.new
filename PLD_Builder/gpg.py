import popen2
import re
import StringIO

import util

def verify_sig(buf):
  """Check signature.
  
  Given email as file-like object, return (signer-emails, signed-body).
  where signer-emails is lists of strings, and signed-body is StringIO
  object.
  """
  (gpg_out, gpg_in, gpg_err) = popen2.popen3("gpg --decrypt")
  util.sendfile(buf, gpg_in)
  gpg_in.close()
  body = StringIO.StringIO()
  for l in gpg_out.xreadlines():
    body.write(l)
  rx = re.compile("^gpg: Good signature from .*<([^>]+)>")
  emails = []
  for l in gpg_err.xreadlines():
    m = rx.match(l)
    if m:
      emails.append(m.group(1))
  body.seek(0)
  gpg_out.close()
  gpg_err.close()
  return (emails, body)

def sign(buf):
  (gpg_out, gpg_in, gpg_err) = popen2.popen3("gpg --clearsign")
  util.sendfile(buf, gpg_in)
  gpg_in.close()
  body = StringIO.StringIO()
  for l in gpg_out.xreadlines():
    body.write(l)
  body.seek(0)
  gpg_out.close()
  gpg_err.close()
  return body

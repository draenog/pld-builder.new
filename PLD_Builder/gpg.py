import popen2
import re
import xreadlines
import StringIO

def verify_sig(buf):
  """Check signature.
  
  Given email as file-like object, return (signer-emails, signed-body).
  where signer-emails is lists of strings, and signed-body is StringIO
  object.
  """
  (gpg_out, gpg_in, gpg_err) = popen2.popen3("LC_ALL=C gpg --decrypt")
  gpg_in.write(buf.read())
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
  (gpg_out, gpg_in, gpg_err) = popen2.popen3("LC_ALL=C gpg --clearsign --default-key builder")
  gpg_in.write(buf.read())
  gpg_in.close()
  body = StringIO.StringIO()
  for l in gpg_out.xreadlines():
    body.write(l)
  body.seek(0)
  gpg_out.close()
  gpg_err.close()
  return body

import popen2
import re

def verify_sig(email):
  """Check signature.
  
  Given email as list of strings, return (signer-emails, signed-body).
  where both are lists of strings.
  """
  (gpg_out, gpg_in, gpg_err) = popen2.popen3("LC_ALL=C gpg --decrypt")
  for l in email:
    gpg_in.write(l)
  gpg_in.close()
  body = gpg_out.readlines()
  rx = re.compile("^gpg: Good signature from .*<([^>]+)>")
  emails = []
  for l in gpg_err.readlines():
    m = rx.match(l)
    if m:
      emails.append(m.group(1))
  return (emails, body)

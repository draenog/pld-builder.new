# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import log
import popen2
import re
import StringIO

import util
import pipeutil

def verify_sig(buf):
    """Check signature.
    
    Given email as file-like object, return (signer-emails, signed-body).
    where signer-emails is lists of strings, and signed-body is StringIO
    object.
    """
    (gpg_out, gpg_in, gpg_err) = popen2.popen3("gpg --batch --no-tty --decrypt")
    try:
        body = pipeutil.rw_pipe(buf, gpg_in, gpg_out)
    except OSError:
        log.error("gnupg signing failed; does gpg binary exist?")
        raise

    rx = re.compile("^gpg: (Good signature from|                aka) .*<([^>]+)>")
    emails = []
    for l in gpg_err.xreadlines():
        m = rx.match(l)
        if m:
            emails.append(m.group(2))
    gpg_err.close()
    return (emails, body)

def sign(buf):
    (gpg_out, gpg_in, gpg_err) = popen2.popen3("gpg --batch --no-tty --clearsign")
    try:
        body = pipeutil.rw_pipe(buf, gpg_in, gpg_out)
    except OSError:
        log.error("gnupg signing failed; does gpg binary exist?")
        raise

    gpg_err.close()
    return body

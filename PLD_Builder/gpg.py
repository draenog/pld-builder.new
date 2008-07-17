# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import log
import popen2
import re
import StringIO

import util
import os
import pipeutil

def __gpg_close(descriptors):
    for d in descriptors:
        if not d.closed:
            d.close()

def get_keys(buf):
    """Extract keys from gpg message

    """

    if not os.path.isfile('/usr/bin/gpg'):
        log.error("missing gnupg binary: /usr/bin/gpg")
        raise OSError, 'Missing gnupg binary'

    gpg_run = popen2.Popen3("/usr/bin/gpg --batch --no-tty --decrypt", True)
    try:
        body = pipeutil.rw_pipe(buf, gpg_run.tochild, gpg_run.fromchild)
    except OSError, e:
        __gpg_close([gpg_run.fromchild, gpg_run.childerr, gpg_run.tochild])
        gpg_run.wait()
        log.error("gnupg run, does gpg binary exist? : %s" % e)
        raise

    rx = re.compile("^gpg: Signature made .*using [DR]SA key ID (.+)")
    keys = []
    for l in gpg_run.childerr.xreadlines():
        m = rx.match(l)
        if m:
            keys.append(m.group(1))

    return keys

def verify_sig(buf):
    """Check signature.

    Given email as file-like object, return (signer-emails, signed-body).
    where signer-emails is lists of strings, and signed-body is StringIO
    object.
    """

    if not os.path.isfile('/usr/bin/gpg'):
        log.error("missing gnupg binary: /usr/bin/gpg")
        raise OSError, 'Missing gnupg binary'

    gpg_run = popen2.Popen3("/usr/bin/gpg --batch --no-tty --decrypt", True)
    try:
        body = pipeutil.rw_pipe(buf, gpg_run.tochild, gpg_run.fromchild)
    except OSError, e:
        __gpg_close([gpg_run.fromchild, gpg_run.childerr, gpg_run.tochild])
        gpg_run.wait()
        log.error("gnupg run failed, does gpg binary exist? : %s" % e)
        raise

    rx = re.compile("^gpg: (Good signature from|                aka) .*<([^>]+)>")
    emails = []
    for l in gpg_run.childerr.xreadlines():
        m = rx.match(l)
        if m:
            emails.append(m.group(2))
    __gpg_close([gpg_run.fromchild, gpg_run.childerr, gpg_run.tochild])
    gpg_run.wait()
    return (emails, body)

def sign(buf):
    if not os.path.isfile('/usr/bin/gpg'):
        log.error("missing gnupg binary: /usr/bin/gpg")
        raise OSError, 'Missing gnupg binary'

    gpg_run  = popen2.Popen3("/usr/bin/gpg --batch --no-tty --clearsign", True)
    try:
        body = pipeutil.rw_pipe(buf, gpg_run.tochild, gpg_run.fromchild)
    except OSError, e:
        __gpg_close([gpg_out, gpg_err, gpg_in])
        gpg_run.wait()
        log.error("gnupg signing failed, does gpg binary exist? : %s" % e)
        raise

    __gpg_close([gpg_run.fromchild, gpg_run.childerr, gpg_run.tochild])
    gpg_run.wait()
    return body

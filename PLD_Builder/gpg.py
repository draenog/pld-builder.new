# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import log
import subprocess
import re
import StringIO

import util
import os
import pipeutil

def get_keys(buf):
    """Extract keys from gpg message

    """

    if not os.path.isfile('/usr/bin/gpg'):
        log.error("missing gnupg binary: /usr/bin/gpg")
        raise OSError, 'Missing gnupg binary'

    d_stdout = None
    d_stderr = None
    cmd = ['/usr/bin/gpg', '--batch', '--no-tty', '--decrypt']
    gpg_run = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    try:
        d_stdout, d_stderr = gpg_run.communicate(buf.read())
    except OSError, e:
        log.error("gnupg run, does gpg binary exist? : %s" % e)
        raise

    rx = re.compile("^gpg: Signature made .*using [DR]SA key ID (.+)")
    keys = []
    
    for l in d_stderr.xreadlines():
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

    d_stdout = None
    d_stderr = None
    cmd = ['/usr/bin/gpg', '--batch', '--no-tty', '--decrypt']
    gpg_run = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    try:
        d_stdout, d_stderr = gpg_run.communicate(buf.read())
    except OSError, e:
        log.error("gnupg run failed, does gpg binary exist? : %s" % e)
        raise

    rx = re.compile("^gpg: (Good signature from|                aka) .*<([^>]+)>")
    emails = []
    for l in d_stderr.split('\n'):
        m = rx.match(l)
        if m:
            emails.append(m.group(2))
    return (emails, d_stdout)

def sign(buf):
    if not os.path.isfile('/usr/bin/gpg'):
        log.error("missing gnupg binary: /usr/bin/gpg")
        raise OSError, 'Missing gnupg binary'

    d_stdout = None
    d_stderr = None
    cmd = ['/usr/bin/gpg', '--batch', '--no-tty', '--clearsign']
    gpg_run = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    try:
        d_stdout, d_stderr = gpg_run.communicate(buf.read())
    except OSError, e:
        log.error("gnupg signing failed, does gpg binary exist? : %s" % e)
        raise

    return d_stdout

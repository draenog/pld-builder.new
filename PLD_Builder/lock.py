# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import fcntl

import path

locks_list = []

def lock(n, non_block = 0):
    f = open(path.lock_dir + n, "a")
    # blah, otherwise it gets garbage collected and doesn't work
    locks_list.append(f)
    if non_block:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except:
            f.close()
            return None
    else:
        fcntl.flock(f, fcntl.LOCK_EX)
    return f

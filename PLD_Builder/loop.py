# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os
import sys
import time

import wrap

def run_loop(fnc, secs = 5, max = 60):
    def run():
        pid = os.fork()
        if pid == 0:
            wrap.wrap(fnc)
            sys.exit(0)
        else:
            pid, s = os.waitpid(pid, 0)
            if os.WIFEXITED(s):
                s = os.WEXITSTATUS(s)
                if s != 0:
                    sys.exit(s)
            else:
                sys.exit(10)

    start = time.time()
    while time.time() - start < max:
        last = time.time()
        run()
        took = time.time() - last
        if took < secs:
            time.sleep(secs - took)


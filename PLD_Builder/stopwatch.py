# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import time
import resource

class Time:
    def __init__(self):
        x = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.user_time = x[0]
        self.sys_time = x[1]
        self.non_io_faults = x[6]
        self.io_faults = x[7]
        self.time = time.time()

    def sub(self, x):
        self.user_time -= x.user_time
        self.sys_time -= x.sys_time
        self.non_io_faults -= x.non_io_faults
        self.io_faults -= x.io_faults
        self.time -= x.time

    def format(self):
        return "user:%.2fs sys:%.2fs real:%.2fs (faults io:%d non-io:%d)" % \
                (self.user_time, self.sys_time, self.time, self.io_faults,
                 self.non_io_faults)

class Timer:
    def __init__(self):
        self.starts = []

    def start(self):
        self.starts.append(Time())

    def stop(self):
        tmp = Time()
        tmp.sub(self.starts.pop())
        return tmp.format()

t = Timer()

def start():
    t.start()

def stop():
    return t.stop()

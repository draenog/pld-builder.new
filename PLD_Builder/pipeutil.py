# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import select
import os
import StringIO

def rw_pipe(buf_, infd, outfd):
    buf = StringIO.StringIO()
    buf.write(buf_.read())
    ret = StringIO.StringIO()
    pos = 0
    rd_fin = 0
    wr_fin = 0
    buf.seek(pos)
    while not (rd_fin and wr_fin):
        if wr_fin: o = []
        else: o = [infd]
        if rd_fin: i = []
        else: i = [outfd]
        i, o, e = select.select(i, o, [])
        if i != []:
            s = os.read(outfd.fileno(), 1000)
            if s == "": rd_fin = 1
            ret.write(s)
        if o != []:
            buf.seek(pos)
            s = buf.read(1000)
            if s == "":
                infd.close()
                wr_fin = 1
            else:
                cnt = os.write(infd.fileno(), s)
                pos += cnt
    outfd.close()
    ret.seek(0)
    return ret

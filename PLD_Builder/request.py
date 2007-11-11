# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

from xml.dom.minidom import *
import string
import time
import xml.sax.saxutils
import fnmatch
import binascii, md5

import util
import log
from acl import acl

__all__ = ['parse_request', 'parse_requests']
    
def text(e):
    res = ""
    for n in e.childNodes:
        if n.nodeType != Element.TEXT_NODE:
            log.panic("xml: text expected in <%s>, got %d" % (e.nodeName, n.nodeType))
        res += n.nodeValue
    return res

def attr(e, a, default = None):
    try:
        return e.attributes[a].value
    except:
        if default != None:
            return default
        raise

def escape(s):
    return xml.sax.saxutils.escape(s)

def is_blank(e):
    return e.nodeType == Element.TEXT_NODE and string.strip(e.nodeValue) == ""
    
class Group:
    def __init__(self, e):
        self.batches = []
        self.kind = 'group'
        self.id = attr(e, "id")
        self.no = int(attr(e, "no"))
        self.priority = 2
        self.time = time.time()
        self.requester = ""
        self.requester_email = ""
        self.flags = string.split(attr(e, "flags", ""))
        for c in e.childNodes:
            if is_blank(c): continue
            if c.nodeType != Element.ELEMENT_NODE:
                log.panic("xml: evil group child %d" % c.nodeType)
            if c.nodeName == "batch":
                self.batches.append(Batch(c))
            elif c.nodeName == "requester":
                self.requester = text(c)
                self.requester_email = attr(c, "email", "")
            elif c.nodeName == "priority":
                self.priority = int(text(c))
            elif c.nodeName == "time":
                self.time = int(text(c))
            else:
                log.panic("xml: evil group child (%s)" % c.nodeName)
        # note that we also check that group is sorted WRT deps
        m = {}
        for b in self.batches:
            deps = []
            m[b.b_id] = b
            for dep in b.depends_on:
                if m.has_key(dep):
                    # avoid self-deps
                    if id(m[dep]) != id(b):
                        deps.append(m[dep])
                else:
                    log.panic("xml: dependency not found in group")
            b.depends_on = deps
        if self.requester_email == "" and self.requester != "":
            self.requester_email = acl.user(self.requester).mail_to()

    def dump(self, f):
        f.write("group: %d (id=%s pri=%d)\n" % (self.no, self.id, self.priority))
        f.write("  from: %s\n" % self.requester)
        f.write("  flags: %s\n" % string.join(self.flags))
        f.write("  time: %s\n" % time.asctime(time.localtime(self.time)))
        for b in self.batches:
            b.dump(f)
        f.write("\n")

    def dump_html(self, f):
        f.write("<p><b>%d</b>. %s from %s <small>%s, %d, %s</small><br/>\n" % \
                (self.no,
                 escape(time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(self.time))),
                 escape(self.requester),
                 self.id, self.priority, string.join(self.flags)))
        f.write("<ul>\n")
        for b in self.batches:
            b.dump_html(f)
        f.write("</ul>\n")
        f.write("</p>\n")

    def write_to(self, f):
        f.write("""
       <group id="%s" no="%d" flags="%s">
         <requester email='%s'>%s</requester>
         <time>%d</time>
         <priority>%d</priority>\n""" % (self.id, self.no, string.join(self.flags),
                    escape(self.requester_email), escape(self.requester), 
                    self.time, self.priority))
        for b in self.batches:
            b.write_to(f)
        f.write("       </group>\n\n")

    def is_done(self):
        ok = 1
        for b in self.batches:
            if not b.is_done():
                ok = 0
        return ok

class Batch:
    def __init__(self, e):
        self.bconds_with = []
        self.bconds_without = []
        self.builders = []
        self.builders_status = {}
        self.kernel = ""
        self.branch = ""
        self.src_rpm = ""
        self.info = ""
        self.spec = ""
        self.command = ""
        self.command_flags = []
        self.gb_id = ""
        self.b_id = attr(e, "id")
        self.depends_on = string.split(attr(e, "depends-on"))
        self.upgraded = True
        for c in e.childNodes:
            if is_blank(c): continue
            if c.nodeType != Element.ELEMENT_NODE:
                log.panic("xml: evil batch child %d" % c.nodeType)
            if c.nodeName == "src-rpm":
                self.src_rpm = text(c)
            elif c.nodeName == "spec":
                self.spec = text(c)
            elif c.nodeName == "command":
                self.spec = "COMMAND"
                self.command = text(c)
                self.command_flags = string.split(attr(c, "flags", ""))
            elif c.nodeName == "info":
                self.info = text(c)
            elif c.nodeName == "kernel":
                self.kernel = text(c)
            elif c.nodeName == "branch":
                self.branch = text(c)
            elif c.nodeName == "builder":
                self.builders.append(text(c))
                self.builders_status[text(c)] = attr(c, "status", "?")
            elif c.nodeName == "with":
                self.bconds_with.append(text(c))
            elif c.nodeName == "without":
                self.bconds_without.append(text(c))
            else:
                log.panic("xml: evil batch child (%s)" % c.nodeName)
 
    def is_done(self):
        ok = 1
        for b in self.builders:
            s = self.builders_status[b]
            if not (s == "OK" or s == "FAIL" or s == "SKIP"):
                ok = 0
        return ok
            
    def dump(self, f):
        f.write("  batch: %s/%s\n" % (self.src_rpm, self.spec))
        f.write("    info: %s\n" % self.info)
        f.write("    kernel: %s\n" % self.kernel)
        f.write("    branch: %s\n" % self.branch)
        f.write("    bconds: %s\n" % self.bconds_string())
        builders = []
        for b in self.builders:
            builders.append("%s:%s" % (b, self.builders_status[b]))
        f.write("    builders: %s\n" % string.join(builders))

    def is_command(self):
        return self.command != ""

    def dump_html(self, f):
        f.write("<li>\n")
        if self.is_command():
            desc = "SH: %s [%s]" % (self.command, ' '.join(self.command_flags))
        else:
            desc = "%s (%s -R %s %s %s)" % \
                (self.src_rpm, self.spec, self.branch, self.bconds_string(), self.kernel_string())
        f.write("%s <small>[" % desc)
        builders = []
        for b in self.builders:
            s = self.builders_status[b]
            if s == "OK":
                c = "green"
            elif s == "FAIL":
                c = "red"
            elif s == "SKIP":
                c = "blue"
            else:
                c = "black"
            link_pre = ""
            link_post = ""
            if (s == "OK" or s == "FAIL") and len(self.spec) > 5:
                if self.is_command():
                    bl_name = "command"
                else:
                    bl_name = self.spec[:len(self.spec)-5]
                lin_ar = b.replace('noauto-','')
                path = "/%s/%s/%s.bz2" % (lin_ar.replace('-','/'), s, bl_name)
                is_ok = 0
                if s == "OK":
                    is_ok = 1
                bld = lin_ar.split('-')
                link_pre = "<a href=\"http://buildlogs.pld-linux.org/index.php?dist=%s&arch=%s&ok=%d&id=%s\">" \
                     % (bld[0], bld[1], is_ok, binascii.b2a_hex(md5.new(path).digest()))
                link_post = "</a>"
            builders.append(link_pre + ("<font color='%s'><b>%s:%s</b></font>" %
                                        (c, b, s)) + link_post)
        f.write("%s]</small></li>\n" % string.join(builders))

    def kernel_string(self):
        r = ""
        if self.kernel != "":
            r = " --define 'alt_kernel " + self.kernel + "'"
        return r

    def bconds_string(self):
        r = ""
        for b in self.bconds_with:
            r = r + " --with " + b
        for b in self.bconds_without:
            r = r + " --without " + b
        return r
        
    def write_to(self, f):
        f.write("""
         <batch id='%s' depends-on='%s'>
           <src-rpm>%s</src-rpm>
           <command flags="%s">%s</command>
           <spec>%s</spec>
           <branch>%s</branch>
           <kernel>%s</kernel>
           <info>%s</info>\n""" % (self.b_id, 
                 string.join(map(lambda (b): b.b_id, self.depends_on)),
                 escape(self.src_rpm), 
                 escape(' '.join(self.command_flags)), escape(self.command),
                 escape(self.spec), escape(self.branch), escape(self.kernel), escape(self.info)))
        for b in self.bconds_with:
            f.write("           <with>%s</with>\n" % escape(b))
        for b in self.bconds_without:
            f.write("           <without>%s</without>\n" % escape(b))
        for b in self.builders:
            f.write("           <builder status='%s'>%s</builder>\n" % \
                                                (escape(self.builders_status[b]), escape(b)))
        f.write("         </batch>\n")
        
    def log_line(self, l):
        log.notice(l)
        if self.logfile != None:
            util.append_to(self.logfile, l)

    def expand_builders(batch, all_builders):
        all = []
        for bld in batch.builders:
            res = []
            for my_bld in all_builders:
                if fnmatch.fnmatch(my_bld, bld):
                    res.append(my_bld)
            if res != []:
                all.extend(res)
            else:
                all.append(bld)
        batch.builders = all

class Notification:
    def __init__(self, e):
        self.batches = []
        self.kind = 'notification'
        self.group_id = attr(e, "group-id")
        self.builder = attr(e, "builder")
        self.batches = {}
        for c in e.childNodes:
            if is_blank(c): continue
            if c.nodeType != Element.ELEMENT_NODE:
                log.panic("xml: evil notification child %d" % c.nodeType)
            if c.nodeName == "batch":
                id = attr(c, "id")
                status = attr(c, "status")
                if status != "OK" and status != "FAIL" and status != "SKIP":
                    log.panic("xml notification: bad status: %s" % self.status)
                self.batches[id] = status
            else:
                log.panic("xml: evil notification child (%s)" % c.nodeName)

    def apply_to(self, q):
        for r in q.requests:
            if r.kind == "group":
                for b in r.batches:
                    if self.batches.has_key(b.b_id):
                        b.builders_status[self.builder] = self.batches[b.b_id]

def build_request(e):
    if e.nodeType != Element.ELEMENT_NODE:
        log.panic("xml: evil request element")
    if e.nodeName == "group":
        return Group(e)
    elif e.nodeName == "notification":
        return Notification(e)
    elif e.nodeName == "command":
        # FIXME
        return Command(e)
    else:
        log.panic("xml: evil request <%s>" % e.nodeName)

def parse_request(f):
    d = parse(f)
    return build_request(d.documentElement)
    
def parse_requests(f):
    d = parse(f)
    res = []
    for r in d.documentElement.childNodes:
        if is_blank(r): continue
        res.append(build_request(r))
    return res

# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

from xml.dom.minidom import *
import string
import time
import xml.sax.saxutils
import fnmatch
import os
import urllib
import cgi

import util
import log
from acl import acl
from config import config

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

# return timestamp with timezone information
# so we could parse it in javascript
def tzdate(t):
    # as strftime %z is unofficial, and does not work, need to make it numeric ourselves
#    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    date = time.strftime("%a %b %d %Y %H:%M:%S", time.localtime(t))
    # NOTE: the altzone is showing CURRENT timezone, not what the "t" reflects
    # NOTE: when DST is off timezone gets it right, altzone not
    if time.daylight:
        tzoffset = time.altzone
    else:
        tzoffset = time.timezone
    tz = '%+05d' % (-tzoffset / 3600 * 100)
    return date + ' ' + tz

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
        self.max_jobs = 0
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
            elif c.nodeName == "maxjobs":
                self.max_jobs = int(text(c))
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
        f.write(
            "<div id=\"%(no)d\" class=\"%(flags)s\">\n"
            "<a href=\"#%(no)d\">%(no)d</a>. <span id=\"tz\">%(time)s</span> from <b>%(requester)s</b> "
            "<small>%(id)s, prio=%(priority)d, jobs=%(max_jobs)d, %(flags)s</small>\n"
        % {
            'no': self.no,
            'id': '<a href="srpms/%(id)s">%(id)s</a>' % {'id': self.id},
            'time': escape(tzdate(self.time)),
            'requester': escape(self.requester),
            'priority': self.priority,
            'max_jobs': self.max_jobs,
            'flags': string.join(self.flags)
        })
        f.write("<ul>\n")
        for b in self.batches:
            b.dump_html(f, self.id)
        f.write("</ul>\n")
        f.write("</div>\n")

    def write_to(self, f):
        f.write("""
       <group id="%s" no="%d" flags="%s">
         <requester email='%s'>%s</requester>
         <time>%d</time>
         <priority>%d</priority>
         <maxjobs>%d</maxjobs>\n""" % (self.id, self.no, string.join(self.flags),
                    escape(self.requester_email), escape(self.requester),
                    self.time, self.priority, self.max_jobs))
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
        self.builders_status_time = {}
        self.builders_status_buildtime = {}
        self.kernel = ""
        self.defines = {}
        self.target = []
        self.branch = ""
        self.src_rpm = ""
        self.info = ""
        self.spec = ""
        self.command = ""
        self.command_flags = []
        self.skip = []
        self.gb_id = ""
        self.b_id = attr(e, "id")
        self.depends_on = string.split(attr(e, "depends-on"))
        self.upgraded = True

        self.parse_xml(e)

        self._topdir = '/tmp/B.%s' % self.b_id

    def parse_xml(self, e):
        for c in e.childNodes:
            if is_blank(c): continue

            if c.nodeType != Element.ELEMENT_NODE:
                log.panic("xml: evil batch child %d" % c.nodeType)
            if c.nodeName == "src-rpm":
                self.src_rpm = text(c)
            elif c.nodeName == "spec":
                # normalize specname, specname is used as buildlog and we don't
                # want to be exposed to directory traversal attacks
                self.spec = text(c).split('/')[-1]
            elif c.nodeName == "command":
                self.spec = "COMMAND"
                self.command = text(c).strip()
                self.command_flags = string.split(attr(c, "flags", ""))
            elif c.nodeName == "info":
                self.info = text(c)
            elif c.nodeName == "kernel":
                self.kernel = text(c)
            elif c.nodeName == "define":
                define = attr(c, "name")
                self.defines[define] = text(c)
            elif c.nodeName == "target":
                self.target.append(text(c))
            elif c.nodeName == "skip":
                self.skip.append(text(c))
            elif c.nodeName == "branch":
                self.branch = text(c)
            elif c.nodeName == "builder":
                key = text(c)
                self.builders.append(key)
                self.builders_status[key] = attr(c, "status", "?")
                self.builders_status_time[key] = attr(c, "time", "0")
                self.builders_status_buildtime[key] = "0" #attr(c, "buildtime", "0")
            elif c.nodeName == "with":
                self.bconds_with.append(text(c))
            elif c.nodeName == "without":
                self.bconds_without.append(text(c))
            else:
                log.panic("xml: evil batch child (%s)" % c.nodeName)

    def get_package_name(self):
        if len(self.spec) <= 5:
            return None
        return self.spec[:-5]

    def tmpdir(self):
        """
        return tmpdir for this batch job building
        """
        # it's better to have TMPDIR and BUILD dir on same partition:
        # + /usr/bin/bzip2 -dc /home/services/builder/rpm/packages/kernel/patch-2.6.27.61.bz2
        # patch: **** Can't rename file /tmp/B.a1b1d3/poKWwRlp to drivers/scsi/hosts.c : No such file or directory
        path = os.path.join(self._topdir, 'BUILD', 'tmp')
        return path

    def is_done(self):
        ok = 1
        for b in self.builders:
            s = self.builders_status[b]
            if not s.startswith("OK") and not s.startswith("SKIP") and not s.startswith("UNSUPP") and not s.startswith("FAIL"):
                ok = 0
        return ok

    def dump(self, f):
        f.write("  batch: %s/%s\n" % (self.src_rpm, self.spec))
        f.write("    info: %s\n" % self.info)
        f.write("    kernel: %s\n" % self.kernel)
        f.write("    defines: %s\n" % self.defines_string())
        f.write("    target: %s\n" % self.target_string())
        f.write("    branch: %s\n" % self.branch)
        f.write("    bconds: %s\n" % self.bconds_string())
        builders = []
        for b in self.builders:
            builders.append("%s:%s" % (b, self.builders_status[b]))
        f.write("    builders: %s\n" % string.join(builders))

    def is_command(self):
        return self.command != ""

    def dump_html(self, f, rid):
        f.write("<li>\n")
        if self.is_command():
            desc = "SH: <pre>%s</pre> flags: [%s]" % (self.command, ' '.join(self.command_flags))
        else:
            package_url = "http://git.pld-linux.org/gitweb.cgi?p=packages/%(package)s.git;f=%(spec)s;h=%(branch)s;a=shortlog" % {
                'spec': self.spec,
                'branch': self.branch,
                'package': self.spec[:-5],
            }
            desc = "%(src_rpm)s (<a href=\"%(package_url)s\">%(spec)s -r %(branch)s</a>%(rpmopts)s)" % {
                'src_rpm': self.src_rpm,
                'spec': self.spec,
                'branch': self.branch,
                'rpmopts': self.bconds_string() + self.kernel_string() + self.target_string() + self.defines_string(),
                'package_url': package_url,
            }
        f.write("%s <small>[" % desc)
        builders = []
        for b in self.builders:
            s = self.builders_status[b]
            if s.startswith("OK"):
                c = "green"
            elif s.startswith("FAIL"):
                c = "red"
            elif s.startswith("SKIP"):
                c = "blue"
            elif s.startswith("UNSUPP"):
                c = "fuchsia"
            else:
                c = "black"
            link_pre = ""
            link_post = ""
            if (s.startswith("OK") or s.startswith("SKIP") or s.startswith("UNSUPP") or s.startswith("FAIL")) and len(self.spec) > 5:
                if self.is_command():
                    bl_name = "command"
                else:
                    bl_name = self.spec[:len(self.spec)-5]
                lin_ar = b.replace('noauto-','')
                path = "/%s/%s/%s,%s.bz2" % (lin_ar.replace('-','/'), s, bl_name, rid)
                is_ok = 0
                if s.startswith("OK"):
                    is_ok = 1
                bld = lin_ar.split('-')
                tree_name = '-'.join(bld[:-1])
                tree_arch = '-'.join(bld[-1:])
                link_pre = "<a href=\"%s/index.php?dist=%s&arch=%s&ok=%d&name=%s&id=%s&action=tail\">" \
                        % (config.buildlogs, urllib.quote(tree_name), urllib.quote(tree_arch), is_ok, urllib.quote(bl_name), urllib.quote(rid))
                link_post = "</a>"

            def ftime(s):
                t = float(s)
                if t > 0:
                    return time.asctime(time.localtime(t))
                else:
                    return 'N/A'

            tooltip = "last update: %(time)s\nbuild time: %(buildtime)s" % {
                'time' : ftime(self.builders_status_time[b]),
                'buildtime' : ftime(self.builders_status_buildtime[b]),
            }
            builders.append(link_pre +
                "<font color='%(color)s'><b title=\"%(tooltip)s\">%(builder)s:%(status)s</b></font>" % {
                    'color' : c,
                    'builder' : b,
                    'status' : s,
                    'tooltip' : cgi.escape(tooltip, True),
            }
            + link_post)
        f.write("%s]</small></li>\n" % string.join(builders))

    def rpmbuild_opts(self):
        """
            return all rpmbuild options related to this build
        """
        rpmopts = self.bconds_string() + self.kernel_string() + self.target_string() + self.defines_string()
        rpmdefs = \
            "--define '_topdir %s' " % self._topdir + \
            "--define '_specdir %{_topdir}' "  \
            "--define '_sourcedir %{_specdir}' " \
            "--define '_rpmdir %{_topdir}/RPMS' " \
            "--define '_builddir %{_topdir}/BUILD' "
        return rpmdefs + rpmopts

    def kernel_string(self):
        r = ""
        if self.kernel != "":
            r = " --define 'alt_kernel " + self.kernel + "'"
        return r

    def target_string(self):
        if len(self.target) > 0:
            return " --target " + ",".join(self.target)
        else:
            return ""

    def bconds_string(self):
        r = ""
        for b in self.bconds_with:
            r = r + " --with " + b
        for b in self.bconds_without:
            r = r + " --without " + b
        return r

    def defines_string(self):
        r = ""
        for key,value in self.defines.items():
            r += " --define '%s %s'" % (key, value)
        return r

    def defines_xml(self):
        r = ""
        for key,value in self.defines.items():
            r += "<define name='%s'>%s</define>\n" % (escape(key), escape(value))
        return r

    def default_target(self, arch):
        self.target.append("%s-pld-linux" % arch)

    def write_to(self, f):
        f.write("""
         <batch id='%s' depends-on='%s'>
           <src-rpm>%s</src-rpm>
           <command flags="%s">%s</command>
           <spec>%s</spec>
           <branch>%s</branch>
           <info>%s</info>\n""" % (self.b_id,
                 string.join(map(lambda (b): b.b_id, self.depends_on)),
                 escape(self.src_rpm),
                 escape(' '.join(self.command_flags)), escape(self.command),
                 escape(self.spec), escape(self.branch), escape(self.info)))
        if self.kernel != "":
            f.write("           <kernel>%s</kernel>\n" % escape(self.kernel))
        for b in self.bconds_with:
            f.write("           <with>%s</with>\n" % escape(b))
        for b in self.target:
            f.write("           <target>%s</target>\n" % escape(b))
        for b in self.bconds_without:
            f.write("           <without>%s</without>\n" % escape(b))
        if self.defines:
            f.write("           %s\n" % self.defines_xml())
        for b in self.builders:
            if self.builders_status_buildtime.has_key(b):
                t = self.builders_status_buildtime[b]
            else:
                t = "0"
            f.write("           <builder status='%s' time='%s' buildtime='%s'>%s</builder>\n" % \
                    (escape(self.builders_status[b]), self.builders_status_time[b], t, escape(b)))
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
        self.batches_buildtime = {}
        for c in e.childNodes:
            if is_blank(c): continue
            if c.nodeType != Element.ELEMENT_NODE:
                log.panic("xml: evil notification child %d" % c.nodeType)
            if c.nodeName == "batch":
                id = attr(c, "id")
                status = attr(c, "status")
                buildtime = attr(c, "buildtime", "0")
                if not status.startswith("OK") and not status.startswith("SKIP") and not status.startswith("UNSUPP") and not status.startswith("FAIL"):
                    log.panic("xml notification: bad status: %s" % status)
                self.batches[id] = status
                self.batches_buildtime[id] = buildtime
            else:
                log.panic("xml: evil notification child (%s)" % c.nodeName)

    def apply_to(self, q):
        for r in q.requests:
            if r.kind == "group":
                for b in r.batches:
                    if self.batches.has_key(b.b_id):
                        b.builders_status[self.builder] = self.batches[b.b_id]
                        b.builders_status_time[self.builder] = time.time()
                        b.builders_status_buildtime[self.builder] = "0" #self.batches_buildtime[b.b_id]

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
        log.panic("xml: evil request [%s]" % e.nodeName)

def parse_request(f):
    d = parseString(f)
    return build_request(d.documentElement)

def parse_requests(f):
    d = parseString(f)
    res = []
    for r in d.documentElement.childNodes:
        if is_blank(r): continue
        res.append(build_request(r))
    return res

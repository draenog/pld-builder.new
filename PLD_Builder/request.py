from xml.dom.minidom import *
import string
import time
import os
import atexit
import xml.sax.saxutils 

import log
import path
import util
import chroot
from acl import acl
import notify

__all__ = ['parse_request', 'parse_requests']
  
def text(e):
  if len(e.childNodes) == 0:
    return ""
  elif len(e.childNodes) == 1:
    n = e.childNodes[0]
    if n.nodeType != Element.TEXT_NODE:
      raise "xml: text expected: <%s>" % e.nodeName
    return n.nodeValue
  else:
    raise "xml: text expected: <%s>" % e.nodeName

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
    self.flags = string.split(attr(e, "flags", ""))
    for c in e.childNodes:
      if is_blank(c): continue
      if c.nodeType != Element.ELEMENT_NODE:
        raise "xml: evil group child %d" % c.nodeType
      if c.nodeName == "batch":
        self.batches.append(Batch(c))
      elif c.nodeName == "requester":
        self.requester = text(c)
      elif c.nodeName == "priority":
        self.priority = int(text(c))
      elif c.nodeName == "time":
        self.time = int(text(c))
      else:
        raise "xml: evil group child (%s)" % c.nodeName
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
          raise "xml: dependency not found in group"
      b.depends_on = deps

  def dump(self, f):
    f.write("group: %d (id=%s pri=%d)\n" % (self.no, self.id, self.priority))
    f.write("  from: %s\n" % self.requester)
    f.write("  flags: %s\n" % string.join(self.flags))
    f.write("  time: %s\n" % time.asctime(time.localtime(self.time)))
    for b in self.batches:
      b.dump(f)
    f.write("\n")

  def write_to(self, f):
    f.write("""
       <group id="%s" no="%d" flags="%s">
         <requester>%s</requester>
         <time>%d</time>
         <priority>%d</priority>\n""" % (self.id, self.no, string.join(self.flags),
                escape(self.requester), self.time, self.priority))
    for b in self.batches:
      b.write_to(f)
    f.write("       </group>\n\n")

  def build_all(r, build_fnc):
    acl.set_current_user(acl.user(r.requester))
    notify.begin(r)
    tmp = path.spool_dir + util.uuid() + "/"
    r.tmp_dir = tmp
    os.mkdir(tmp)
    atexit.register(util.clean_tmp, tmp)
  
    log.notice("started processing %s" % r.id)
    r.chroot_files = []
    r.some_ok = 0
    for batch in r.batches:
      can_build = 1
      failed_dep = ""
      for dep in batch.depends_on:
        if dep.build_failed:
          can_build = 0
          failed_dep = dep.spec
          
      if can_build:
        log.notice("building %s" % batch.spec)
        batch.logfile = tmp + batch.spec + ".log"
        batch.build_failed = build_fnc(r, batch)
        if batch.build_failed:
          log.notice("building %s FAILED" % batch.spec)
          notify.add_batch(batch, "FAIL")
        else:
          r.some_ok = 1
          log.notice("building %s OK" % batch.spec)
          notify.add_batch(batch, "OK")
      else:
        batch.build_failed = 1
        batch.skip_reason = "SKIPED [%s failed]" % failed_dep
        batch.logfile = None
        log.notice("building %s %s" % (batch.spec, batch.skip_reason))
        notify.add_batch(batch, "SKIP")

  def clean_files(r):
    chroot.run("rm -f %s" % string.join(r.chroot_files))

  def send_report(r):
    def names(l): return map(lambda (b): b.spec, l)
    s_failed = filter(lambda (x): x.build_failed, r.batches)
    s_ok = filter(lambda (x): not x.build_failed, r.batches)
    subject = ""
    if s_failed != []:
      subject += " ERRORS: " + string.join(names(s_failed))
    if s_ok != []:
      subject += " OK: " + string.join(names(s_ok))
    
    m = acl.user(r.requester).message_to()
    m.set_headers(subject = subject[0:100])

    for b in r.batches:
      if b.build_failed and b.logfile == None:
        info = b.skip_reason
      elif b.build_failed: 
        info = "FAILED"
      else: 
        info = "OK"
      m.write("%s (%s): %s\n" % (b.spec, b.branch, info))
    
    for b in r.batches:
      # FIXME: include unpackaged files section
      if b.build_failed and b.logfile != None:
        m.write("\n\n*** buildlog for %s\n" % b.spec)
        m.append_log(b.logfile)
        m.write("\n\n")
        
    m.send()

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
    self.branch = ""
    self.src_rpm = ""
    self.info = ""
    self.spec = ""
    self.b_id = attr(e, "id")
    self.depends_on = string.split(attr(e, "depends-on"))
    for c in e.childNodes:
      if is_blank(c): continue
      if c.nodeType != Element.ELEMENT_NODE:
        raise "xml: evil batch child %d" % c.nodeType
      if c.nodeName == "src-rpm":
        self.src_rpm = text(c)
      elif c.nodeName == "spec":
        self.spec = text(c)
      elif c.nodeName == "info":
        self.info = text(c)
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
        raise "xml: evil batch child (%s)" % c.nodeName
 
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
    f.write("    branch: %s\n" % self.branch)
    f.write("    bconds: %s\n" % self.bconds_string())
    builders = []
    for b in self.builders:
      builders.append("%s:%s" % (b, self.builders_status[b]))
    f.write("    builders: %s\n" % string.join(builders))

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
           <spec>%s</spec>
           <branch>%s</branch>
           <info>%s</info>\n""" % (self.b_id, 
             string.join(map(lambda (b): b.b_id, self.depends_on)),
             escape(self.src_rpm), 
             escape(self.spec), escape(self.branch), escape(self.info)))
    for b in self.bconds_with:
      f.write("           <with>%s</with>\n" % escape(b))
    for b in self.bconds_without:
      f.write("           <without>%s</without>\n" % escape(b))
    for b in self.builders:
      f.write("           <builder status='%s'>%s</builder>\n" % \
                        (escape(self.builders_status[b]), escape(b)))
    f.write("         </batch>\n")

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
        raise "xml: evil notification child %d" % c.nodeType
      if c.nodeName == "batch":
        id = attr(c, "id")
        status = attr(c, "status")
        if status != "OK" and status != "FAIL" and status != "SKIP":
          raise "xml notification: bad status: %s" % self.status
        self.batches[id] = status
      else:
        raise "xml: evil notification child (%s)" % c.nodeName

  def apply_to(self, q):
    for r in q.requests:
      if r.kind == "group":
        for b in r.batches:
          if self.batches.has_key(b.b_id):
            b.builders_status[self.builder] = self.batches[b.b_id]

def build_request(e):
  if e.nodeType != Element.ELEMENT_NODE:
    raise "xml: evil request element"
  if e.nodeName == "group":
    return Group(e)
  elif e.nodeName == "notification":
    return Notification(e)
  elif e.nodeName == "command":
    # FIXME
    return Command(e)
  else:
    raise "xml: evil request <%s>" % e.nodeName

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

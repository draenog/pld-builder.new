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
  if default != None and not e.attributes.has_key(a):
    return default
  return e.attributes[a].value

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

  def dump(self):
    print "group: %s @%d" % (self.id, self.priority)
    print "  from: %s" % self.requester
    print "  time: %s" % time.asctime(time.localtime(self.time))
    for b in self.batches:
      b.dump()

  def write_to(self, f):
    f.write("""
       <group id="%s" no="%d">
         <requester>%s</requester>
         <time>%d</time>
         <priority>%d</priority>\n""" % (self.id, self.no, 
                escape(self.requester), self.time, self.priority))
    for b in self.batches:
      b.write_to(f)
    f.write("       </group>\n\n")

  def build_all(r, build_fnc):
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
        else:
          r.some_ok = 1
          log.notice("building %s OK" % batch.spec)
      else:
        batch.build_failed = 1
        batch.skip_reason = "SKIPED [%s failed]" % failed_dep
        batch.logfile = None
        log.notice("building %s %s" % (batch.spec, batch.skip_reason))

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

class Batch:
  def __init__(self, e):
    self.bconds_with = []
    self.bconds_without = []
    self.builders = []
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
      elif c.nodeName == "with":
        self.bconds_with.append(text(c))
      elif c.nodeName == "without":
        self.bconds_without.append(text(c))
      else:
        raise "xml: evil batch child (%s)" % c.nodeName
  
  def dump(self):
    print "  batch: %s/%s" % (self.src_rpm, self.spec)
    print "    info: %s" % self.info
    print "    branch: %s" % self.branch
    print "    bconds: %s" % self.bconds_string()
    print "    for: %s" % string.join(self.builders)

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
      f.write("           <builder>%s</builder>\n" % escape(b))
    f.write("         </batch>\n")

def build_request(e):
  if e.nodeType != Element.ELEMENT_NODE:
    raise "xml: evil request element"
  if e.nodeName == "group":
    return Group(e)
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

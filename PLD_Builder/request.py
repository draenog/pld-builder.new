from xml.dom.minidom import *
import string
import time
import xml.sax.saxutils 

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

def attr(e, a):
  return e.attributes[a].value

def escape(s):
  return xml.sax.saxutils.escape(s)

def is_blank(e):
  return e.nodeType == Element.TEXT_NODE and string.strip(e.nodeValue) == ""
  
class Group:
  def __init__(self, e):
    self.batches = []
    self.is_group = 1
    self.id = attr(e, "id")
    self.no = int(attr(e, "no"))
    self.priority = 2
    self.time = time.time()
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

class Batch:
  def __init__(self, e):
    self.bconds_with = []
    self.bconds_without = []
    self.builders = []
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
    print "    with: %s" % string.join(self.bconds_with)
    print "    without: %s" % string.join(self.bconds_without)
    print "    for: %s" % string.join(self.builders)

  def write_to(self, f):
    f.write("""
         <batch>
           <src-rpm>%s</src-rpm>
           <spec>%s</spec>
           <info>%s</info>\n\n""" % (escape(self.src_rpm), 
                                   escape(self.spec), escape(self.info)))
    for b in self.bconds_with:
      f.write("           <with>%s</with>\n" % escape(b))
    f.write("\n")
    for b in self.bconds_without:
      f.write("           <without>%s</without>\n" % escape(b))
    f.write("\n")
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

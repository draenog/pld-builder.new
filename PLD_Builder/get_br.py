import re
import string
import xreadlines
from util import *


def get_build_requires(spec, bconds_with, bconds_without):
  cond_rx = re.compile(r"%\{(\!\?|\?\!|\?)([a-zA-Z0-9_+]+)\s*:([^%\{\}]*)\}")
  
  def expand_conds(l):
    def expand_one(m):
      if m.group(1) == "?":
        if macros.has_key(m.group(2)):
          return m.group(3)
      else:
        if not macros.has_key(m.group(2)):
          return m.group(3)
      return ""
    
    for i in range(10):
      l = cond_rx.sub(expand_one, l)
      if len(l) > 1000: break

    return l

  macro_rx = re.compile(r"%\{([a-zA-Z0-9_+]+)\}")
  def expand_macros(l):
    def expand_one(m):
      if macros.has_key(m.group(1)):
        return string.strip(macros[m.group(1)])
      else:
        return m.group(0) # don't change
        
    for i in range(10):
      l = macro_rx.sub(expand_one, l)
      if len(l) > 1000: break
      
    return expand_conds(l)
  
  simple_br_rx = re.compile(r"^BuildRequires\s*:\s*([^\s]+)", re.I)
  bcond_rx = re.compile(r"^%bcond_(with|without)\s+([^\s]+)")
  version_rx = re.compile(r"^Version\s*:\s*([^\s]+)", re.I)
  release_rx = re.compile(r"^Release\s*:\s*([^\s]+)", re.I)
  name_rx = re.compile(r"^Name\s*:\s*([^\s]+)", re.I)
  define_rx = re.compile(r"^\%define\s+([a-zA-Z0-9_+]+)\s+(.*)", re.I)
  any_br_rx = re.compile(r"BuildRequires", re.I)
  
  macros = {}
  for b in bconds_with:
    macros["_with_%s" % b] = 1
  for b in bconds_without:
    macros["_without_%s" % b] = 1

  macros["__perl"] = "/usr/bin/perl"
  macros["_bindir"] = "/usr/bin"
  macros["_sbindir"] = "/usr/bin"
  macros["kgcc_package"] = "gcc"

  build_req = []
    
  f = open(spec)
  for l in xreadlines.xreadlines(f):
    l = string.strip(l)
    if l == "%changelog": break
    
    # %bcond_with..
    m = bcond_rx.search(l)
    if m:
      bcond = m.group(2)
      if m.group(1) == "with":
        if macros.has_key("_with_%s" % bcond): 
          macros["with_%s" % bcond] = 1
      else:
        if not macros.has_key("_without_%s" % bcond): 
          macros["with_%s" % bcond] = 1
      continue
  
    # name,version,release
    m = version_rx.search(l)
    if m: macros["version"] = m.group(1)
    m = release_rx.search(l)
    if m: macros["release"] = m.group(1)
    m = name_rx.search(l)
    if m: macros["name"] = m.group(1)

    # %define
    m = define_rx.search(l)
    if m: macros[m.group(1)] = m.group(2)
    
    # *BuildRequires*
    if any_br_rx.search(l):
      l = expand_macros(l)
      m = simple_br_rx.search(l)
      if m:
        build_req.append(m.group(1))
      else:
        if l <> "" and l[0] <> '#':
          msg("spec error (%s): %s\n" % (spec, l))

  for x in build_req:
    print x

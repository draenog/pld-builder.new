import ConfigParser
import string
import os

import path
import log

class Builder_Conf:
  def __init__(self):
    pass

  def read(self, builder):
    p = ConfigParser.ConfigParser()
    def get(o, d = None):
      if p.has_option(builder, o):
        return p.get(builder, o)
      elif p.has_option("all", o):
        return p.get("all", o)
      elif d != None:
        return d
      else:
        log.panic("cannot find %s::%s" % (builder, d))
        
    p.readfp(open(path.builder_conf))
    if builder not in p.sections():
      log.panic("builder %s not in config file" % builder)
    self.builder = builder
    self.arch = get("arch")
    self.chroot = get("chroot")
    self.email = get("email")

config = Builder_Conf()

def init_conf(builder):
  os.environ['LC_ALL'] = "C"
  config.read(builder)

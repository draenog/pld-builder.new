import ConfigParser
import string
import os

import path
import log
import status

class Builder_Conf:
  def __init__(self):
    self.done = 0
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
        log.panic("cannot find %s::%s" % (builder, o))
    
    p.readfp(open(path.builder_conf))

    if builder == "src":
      builder = get("src_builder", builder)
    self.builder = builder

    self.binary_builders = string.split(get("binary_builders"))
    self.control_url = get("control_url")
    self.queue_signed_by = get("queue_signed_by")
    self.notify_email = get("notify_email")
    self.admin_email = get("admin_email")
    self.email = self.admin_email

    if builder == "all":
      return

    if builder not in p.sections():
      log.panic("builder %s not in config file" % builder)
    self.arch = get("arch")
    self.chroot = get("chroot")
    self.email = get("email")
    self.buildlogs_url = get("buildlogs_url")
    self.ftp_url = get("ftp_url")
    self.job_slots = int(get("job_slots"))
    self.max_load = float(get("max_load"))
    self.control_url = get("control_url")
    self.done = 1

config = Builder_Conf()

def init_conf(builder):
  os.environ['LC_ALL'] = "C"
  status.push("reading builder config")
  log.builder = builder
  if builder == "": builder = "all"
  config.read(builder)
  log.builder = config.builder
  status.pop()

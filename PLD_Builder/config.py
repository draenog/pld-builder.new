import ConfigParser
import string
import os
import syslog

import path
import log
import status


syslog_facilities = {
  'kern': syslog.LOG_KERN,
  'user': syslog.LOG_USER,
  'mail': syslog.LOG_MAIL,
  'daemon': syslog.LOG_DAEMON,
  'auth': syslog.LOG_AUTH,
  'lpr': syslog.LOG_LPR,
  'news': syslog.LOG_NEWS,
  'uucp': syslog.LOG_UUCP,
  'cron': syslog.LOG_CRON,
  'local0': syslog.LOG_LOCAL0,
  'local1': syslog.LOG_LOCAL1,
  'local2': syslog.LOG_LOCAL2,
  'local3': syslog.LOG_LOCAL3,
  'local4': syslog.LOG_LOCAL4,
  'local5': syslog.LOG_LOCAL5,
  'local6': syslog.LOG_LOCAL6,
  'local7': syslog.LOG_LOCAL7
}

class Builder_Conf:
  def __init__(self):
    self.done = 0
    pass

  def read(self, builder):
    p = ConfigParser.ConfigParser()
    def get(o, d = None):
      if p.has_option(builder, o):
        return string.strip(p.get(builder, o))
      elif p.has_option("all", o):
        return string.strip(p.get("all", o))
      elif d != None:
        return d
      else:
        log.panic("cannot find %s::%s" % (builder, o))
    
    p.readfp(open(path.builder_conf))

    if p.has_option("all", "syslog"):
      f = p.get("all", "syslog")
      if f != "":
        if syslog_facilities.has_key(f):
          log.open_syslog("builder", syslog_facilities[f])
        else:
          log.panic("no such syslog facility: %s" % f)

    if builder == "src":
      builder = get("src_builder", builder)
    self.builder = builder

    self.binary_builders = string.split(get("binary_builders"))
    self.tag_prefixes = string.split(get("tag_prefixes", ""))
    self.bot_channel = get("bot_channel")
    self.bot_email = get("bot_email")
    self.control_url = get("control_url")
    self.notify_email = get("notify_email")
    self.admin_email = get("admin_email")
    self.builder_list = get("builder_list", "")
    status.admin = self.admin_email
    status.builder_list = self.builder_list
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
    self.test_ftp_url = get("test_ftp_url")
    self.job_slots = int(get("job_slots"))
    self.max_load = float(get("max_load"))
    self.control_url = get("control_url")
    self.builder_user = get("builder_user", "builder")
    self.sudo_chroot_wrapper = get("sudo_chroot_wrapper", "")
    
    f = get("syslog", "")
    if f != "":
      if syslog_facilities.has_key(f):
        log.open_syslog(self.builder, syslog_facilities[f])
      else:
        log.panic("no such syslog facility: %s" % f)

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

import ConfigParser
import string

import path
import log
import status
from mailer import Message
from config import config

class User:
  def __init__(self, p, login):
    self.login = login
    self.privs = []
    self.emails = []
    
    if p.has_option(login, "emails"):
      self.emails = string.split(p.get(login, "emails"))
    else:
      log.alert("acl: [%s] has no emails" % login)
      
    if p.has_option(login, "privs"):
      for p in string.split(p.get(login, "privs")):
        l = string.split(p, ":")
        if len(l) != 2 or l[0] == "" or l[1] == "":
          log.alert("acl: invalid priv format: '%s' [%s]" % (p, login))
        else:
          self.privs.append((l[0], l[1]))
    else:
      log.alert("acl: [%s] has no privs" % login)

  def can_do(self, what, where):
    # TODO: use fnmatch
    for (pwhat, pwhere) in self.privs:
      if pwhat[0] == "!":
        ret = 0
        pwhat = pwhat[1:]
      else:
        ret = 1
      if pwhat == "*" or pwhat == what:
        if pwhere == "*" or pwhere == where:
          return ret

    return 0

  def mail_to(self):
    return self.emails[0]

  def message_to(self):
    m = Message()
    m.set_headers(to = self.mail_to())
    return m

  def get_login(self):
    return self.login

class ACL_Conf:
  def __init__(self):
    self.current_user = ""
    status.push("reading acl.conf")
    p = ConfigParser.ConfigParser()
    p.readfp(open(path.acl_conf))
    self.users = {}
    for login in p.sections():
      user = User(p, login)
      for e in user.emails:
        self.users[e] = user
      self.users[login] = user
    status.pop()
  
  def user_by_email(self, ems):
    for e in ems:
      if self.users.has_key(e):
        self.current_user = self.users[e].login
        return self.users[e]
    return None

  def user(self, l):
    return self.users[l]

acl = ACL_Conf()

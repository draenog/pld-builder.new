# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import ConfigParser
import string
import fnmatch
import os
import stat

import path
import log
import status
from mailer import Message
from config import config

class User:
    def __init__(self, p, login):
        self.login = login
        self.privs = []
        self.gpg_emails = []
        self.mailto = ""

        if p.has_option(login, "gpg_emails"):
            self.gpg_emails = string.split(p.get(login, "gpg_emails"))
        else:
            log.panic("acl: [%s] has no gpg_emails" % login)

        if p.has_option(login, "mailto"):
            self.mailto = p.get(login, "mailto")
        else:
            if len(self.gpg_emails) > 0:
                self.mailto = self.gpg_emails[0]

        if p.has_option(login, "privs"):
            for p in string.split(p.get(login, "privs")):
                l = string.split(p, ":")
                if len(l) == 2:
                    p+=":*"
                if len(l) not in (2,3) or l[0] == "" or l[1] == "":
                    log.panic("acl: invalid priv format: '%s' [%s]" % (p, login))
                else:
                    self.privs.append(p)
        else:
            log.panic("acl: [%s] has no privs" % login)

    def can_do(self, what, where, branch=None):
        if branch:
            action = "%s:%s:%s" % (what, where, branch)
        else:
            action = "%s:%s:N-A" % (what, where)
        for priv in self.privs:
            if priv[0] == "!":
                ret = 0
                priv = priv[1:]
            else:
                ret = 1
            pwhat,pwhere,pbranch=priv.split(":")
            for pbranch in pbranch.split(","):
                priv="%s:%s:%s" % (pwhat,pwhere,pbranch)
                if fnmatch.fnmatch(action, priv):
                    return ret
        return 0

    def check_priority(self, prio, where):
        for priv in self.privs:
            val,builder=priv.split(":")[0:2]
            if fnmatch.fnmatch(where, builder):
                try:
                    val=int(val)
                except ValueError:
                    continue
                if prio>=val:
                    return prio
                else:
                    return val
        return prio

    def mail_to(self):
        return self.mailto

    def message_to(self):
        m = Message()
        m.set_headers(to = self.mail_to(), cc = config.builder_list)
        return m

    def get_login(self):
        return self.login

class ACL_Conf:
    def __init__(self):
        self.reload()

    def try_reload(self):
        mtime = os.stat(path.acl_conf)[stat.ST_MTIME]
        if mtime != self.acl_conf_mtime:
            log.notice("acl.conf has changed, reloading...")
            self.reload()
            return True
        return False

    def reload(self):
        self.acl_conf_mtime = os.stat(path.acl_conf)[stat.ST_MTIME]
        self.current_user = None
        status.push("reading acl.conf")
        p = ConfigParser.ConfigParser()
        p.readfp(open(path.acl_conf))
        self.users = {}
        for login in p.sections():
            if self.users.has_key(login):
                log.panic("acl: duplicate login: %s" % login)
                continue
            user = User(p, login)
            for e in user.gpg_emails:
                if self.users.has_key(e):
                    log.panic("acl: user email colision %s <-> %s" % \
                              (self.users[e].login, login))
                else:
                    self.users[e] = user
            self.users[login] = user
        status.pop()

    def user_by_email(self, ems):
        for e in ems:
            if self.users.has_key(e):
                return self.users[e]
        return None

    def user(self, l):
        if not self.users.has_key(l):
            log.panic("no such user: %s" % l)
        return self.users[l]

    def set_current_user(self, u):
        self.current_user = u
        if u != None:
            status.email = u.mail_to()

    def current_user_login(self):
        if self.current_user != None:
            return self.current_user.login
        else:
            return ""

acl = ACL_Conf()

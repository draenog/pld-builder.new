#! /usr/bin/python

# As omta segfaults and rest is so huge and does't work out of box
# mailer="./smtpwrapper.py" or whatever path is

smtp_host = "beauty.ant.vpn"

import smtplib,sys

msg = sys.stdin.read()

server = smtplib.SMTP(smtp_host)
# server.set_debuglevel(1)
server.sendmail("matkor@pld-linux.org","builder-ac@pld-linux.org", msg) # Adresses should be taken from .requestrc
server.quit()


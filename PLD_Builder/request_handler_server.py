#!/usr/bin/python

import socket
import string
import cgi
import time
import log
import sys
import traceback
import os
from config import config, init_conf

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import request_handler
import path

class MyHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		self.send_error(401);

	def do_POST(self):
		global rootnode
		try:
			length = int(self.headers.getheader('content-length'))
			ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype != 'application/x-www-form-urlencoded':
				log.error("request_handler_server: [%s]: 401 Unauthorized" % self.client_address[0])
				self.send_error(401)
				self.end_headers()
				return

			query = self.rfile.read(length)

			filename = self.headers.getheader('x-filename')

			if not request_handler.handle_request_main(query, filename = filename):
				error = log.last_log();
				log.error("request_handler_server: [%s]: handle_request_main(..., %s) failed" % (self.client_address[0], filename))
				self.send_error(500, "%s: request failed. %s" % (filename, error))
				self.end_headers()
				return

			self.send_response(200)
			self.end_headers()

		except Exception, e:
			self.send_error(500, "%s: %s" % (filename, e))
			self.end_headers()
			log.error("request_handler_server: [%s]: exception: %s\n%s" % (self.client_address[0], e, traceback.format_exc()))
			raise
			pass

def write_css():
	css_file = path.www_dir + "/style.css"
	# skip if file exists and code is not newer
	if os.path.exists(css_file) and os.stat(__file__).st_mtime < os.stat(css_file).st_mtime:
		return

	# css from www.pld-linux.org wiki theme, using css usage firebug plugin to cleanup
	css = """
html {
	background-color: white;
	color: #5e5e5e;
	font-family: Tahoma, Arial, Lucida Grande, sans-serif;
	font-size: 0.75em;
	line-height: 1.25em;
}

a {
	text-decoration: underline;
	color: #006;
}

a:hover {
	color: #006;
}

pre {
	background: #FFF8EB;
	border: 1pt solid #FFE2AB;
	font-family: courier, monospace;
	padding: 0.5em;
	white-space: pre-wrap;
	word-wrap: break-word;
}

@media screen, projection {
	html {
		background-color: #f3efe3;
	}

	body {
		position: relative;
	}

	div {
		background-color: white;
		margin: 10px 0px;
		padding: 2px;
	}
	div > a {
		font-weight: bold;
		color: #5e5e5e;
	}
	div > a:hover {
		color: #5e5e5e;
	}
	div:target {
		background-color: #ffffcc;
		color: black;
	}
}
@media print {
	a {
		background-color: inherit;
		color: inherit;
	}
}

@media projection {
	html { line-height: 1.8em; }
	body, b, a, p { font-size: 22pt; }
}
"""
	old_umask = os.umask(0022)
	f = open(css_file, "w")
	f.write(css)
	f.close()
	os.umask(old_umask)

def main():
	write_css();
	socket.setdefaulttimeout(30)
	try:
		init_conf()
		host = ""
		port = config.request_handler_server_port

		try:
			server = HTTPServer((host, port), MyHandler)
		except Exception, e:
			log.notice("request_handler_server: can't start server on [%s:%d]: %s" % (host, port, e))
			print >> sys.stderr, "ERROR: Can't start server on [%s:%d]: %s" % (host, port, e)
			sys.exit(1)

		log.notice('request_handler_server: started on [%s:%d]...' % (host, port))
		server.serve_forever()
	except KeyboardInterrupt:
		log.notice('request_handler_server: ^C received, shutting down server')
		server.socket.close()

if __name__ == '__main__':
	main()


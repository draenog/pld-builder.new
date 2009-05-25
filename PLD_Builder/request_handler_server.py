#!/usr/bin/python

import socket
import string
import cgi
import time
import log
import sys
import traceback
from config import config, init_conf

from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import request_handler

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

def main():
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


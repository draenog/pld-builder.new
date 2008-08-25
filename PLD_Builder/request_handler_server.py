#!/usr/bin/python

host = ""
port = 1234


import string
import cgi
import time
import StringIO

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
				self.send_error(401)
				self.end_headers()
				return

			query = self.rfile.read(length)
			sio = StringIO.StringIO()
			sio.write(query)
			sio.seek(0)

			filename = self.headers.getheader('x-filename')

			if not request_handler.handle_request_main(sio, filename = filename):
				self.send_error(500)
				self.end_headers()
				return

			self.send_response(200)
			self.end_headers()

		except Exception, e:
			self.send_error(500)
			self.end_headers()
			raise
			pass

def main():
	try:
		server = HTTPServer((host, port), MyHandler)
		print 'started httpserver...'
		server.serve_forever()
	except KeyboardInterrupt:
		print '^C received, shutting down server'
		server.socket.close()

if __name__ == '__main__':
	main()


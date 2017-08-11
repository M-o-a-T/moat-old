# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This code implements the state machine for a single link device.
"""

import asyncio
import binascii

class LinkDevice(object):
	def __init__(self, prefix, loop=None):
		self.prefix = prefix
		self.streams = dict()
		self.cons = ''
		self.cons_dir = None
		self.cons_writer = None
		self.loop = loop or asyncio.get_event_loop()

	def dump_console(self):
		if self.cons != "":
			if self.cons[:-1] == "\r":
				print(">>> " if self.cons_dir else "::: ", self.prefix)
			else:
				print(">>>." if self.cons_dir else ":::.", self.prefix)
			print(self.cons[:-1].replace("\r","\n  "))
		self.cons_dir = None
		self.cons = ""

	def dump_bin(self,out,stream,data):
		print(self.prefix, '<' if out else '>', '%02x:'%stream, ' '.join('%02x'%x for x in data),
			'', ''.join('.' if c<32 else chr(c) for c in data))

	def has_send(self,stream,data, verbose=0):
		if verbose:
			self.dump_bin(True,stream,data)
		if stream == 0: # console
			if self.cons_dir is False:
				self.dump_console()
				self.cons_dir = True

		elif stream == 1: # config
			pass
		else:
			pass

	def has_recv(self,stream,data, verbose=0):
		if verbose:
			self.dump_bin(False,stream,data)
		

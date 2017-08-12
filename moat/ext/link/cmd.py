# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

"""Handle event logging for graphing"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import types
import binascii
from pprint import pprint
from sqlmix.async import Db,NoData
from qbroker.unit import CC_DICT, CC_DATA, CC_MSG
from qbroker.util import UTC
from yaml import dump
from traceback import print_exc
from boltons.iterutils import remap
from datetime import datetime

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK
from moat.times import simple_time_delta, humandelta
from .dev import LinkDevice
from . import PREFIX, key_parts,key_build

import logging
logger = logging.getLogger(__name__)

__all__ = ['LinkCommand']

## TODO add --dest UUID

def add_human(d):
	"""add human-readable tags"""
	for k in "interval max_age".split():
		v = d.get(k,None)
		if v is not None:
			d.setdefault('human',{})[k] = humandelta(v)
	m = d.get('method',None)
	if m is not None:
		d.setdefault('human',{})['method'] = modes[m]

class _Command(Command):
	pass

class LogCommand(_Command):
	name = "log"
	summary = "Log the packet stream on AMQP"
	description = """\
Log the event stream to any or all link adapters.

"""
	async def do(self,args):
		await self.setup()
		self.quitting = asyncio.Event(loop=self.root.loop)

		self.u = await self.root._get_amqp()
		n = list(PREFIX[:])
		if not args:
			n.append('#')
		else:
			n.append(args[0])
			if len(args) == 1:
				n.append("#")
			else:
				n.append("*")
				n += args[1:]

		self.dev = dict()
		await self.u.register_alert_async('.'.join(n), self.callback, call_conv=CC_MSG)
		if self.root.verbose > 1:
			print("listening on",'.'.join(n))
		await self.quitting.wait()

	def report_bad(self, msg):
		data = repr(msg.data)
		if isinstance(msg.data,type(b'')):
			data = data[2:-1]
		print("BAD",msg.routing_key, ' '.join('%02x'%x for x in msg.data), data)

	async def callback(self, msg):
		try:
			body = msg.data
			rk = msg.routing_key
			devname,io,chans,stream = key_parts(rk)
			devname = '.'.join(devname)
			if chans:
				chans = '.'.join(chans)
			else:
				chans = '*'
			devname += '.'+chans
			try:
				dev = self.dev[devname]
			except KeyError:
				self.dev[devname] = dev = LinkDevice(devname, loop=self.root.loop)
			if io is False:
				dev.has_recv(stream,body, verbose=self.root.verbose)
			elif io is True:
				dev.has_send(stream,body, verbose=self.root.verbose)
			else:
				self.report_bad(msg)

		except Exception as exc:
			self.report_bad(msg)
			logger.exception("Problem processing %s", repr(body))
			self.quitting.set()

class RawCommand(_Command):
	name = "raw"
	summary = "send some raw data"
	description = """\
This command sends raw data to a device.

"""

	def addOptions(self):
		self.parser.add_option('-s','--stream',
			action="store", dest="stream", type="int", default=0,
			help="Stream to use. Default: console.")
		self.parser.add_option('-S','--seq',
			action="store", dest="seq", type=int, default=0,
			help="Sequence# for console messages. Default: zero.")
		self.parser.add_option('-c','--channels',
			action="store", dest="channels", nargs='+',
			help="Channel to send to")
		self.parser.add_option('-a','--ascii',
			action="store_const", const=True, dest="ascii",
			help="Text message (otherwise: hex bytes)")
		self.parser.add_option('--in',
			action="store_const", const=True, dest="dir_in",
			help="Fake an incoming message")
		self.parser.add_option('--error',
			action="store_const", const=True, dest="dir_error",
			help="Fake an error message")

	async def do(self,args):
		if not len(args):
			raise SyntaxError("Usage: … raw devicename hexbyte…")
		device = args[0]
		args = args[1:]
		opts = self.options
		if opts.dir_in and opts.dir_error:
			raise SyntaxError("--in and --error are mutually exclusive")
		if opts.stream and opts.seq:
			raise SyntaxError("--seq only makes sense on the console (channel zero)")

		self.u = await self.root._get_amqp()
		await self.setup()
		rk = key_build(device, None if opts.dir_error else not opts.dir_in,
				opts.channels, opts.stream)
		if len(args) == 1 and args[0] == "-":
			data = sys.stdin.read()
		elif opts.ascii:
			data = ' '.join(args).encode("utf-8")
		else:
			data = binascii.unhexlify(''.join(args))

		if not opts.stream:
			data = chr(opts.seq).encode("latin1")+data
		await self.u.alert(rk, data, codec="application/binary")


class LinkCommand(SubCommand):
	name = "link"
	summary = "Handle IoT links"
	description = """\
Commands to control links and to send and log link messages.
"""

	# process in order
	subCommandClasses = [
		LogCommand,
		RawCommand,
	]



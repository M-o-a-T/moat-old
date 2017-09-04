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

"""Talk to the broker directly"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
from qbroker.unit import CC_DATA, CC_MSG
from yaml import dump
from traceback import print_exc
from pprint import pprint

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK

import logging
logger = logging.getLogger(__name__)

__all__ = ['BrokerCommand']

## TODO add --dest UUID

class CmdCommand(Command):
	name = "cmd"
	summary = "Send an arbitrary command on the bus",
	description = """\
Send an arbitrary command to the bus.

Arguments:
* routing key
* any number of name=value pairs
"""
	_alert = False

	def addOptions(self):
		self.parser.add_option('-u','--uuid',
			action="store", dest="uuid",
			help="Query this UUID directly")
		self.parser.add_option('-t','--timeout',
			action="store", dest="timeout", type="int",
			default=60 if not self._alert else 3,
			help="Timeout")
		self.parser.add_option('-c','--rpc',
			action="store", dest="rpc", default="moat.cmd" if not self._alert else None,
			help="Routing key")

	async def do(self,args):
		if not self._alert and len(args) < 1:
			raise SyntaxError("Usage: %s  words to send  var=data.to.add" % (self.name,))
		if self.options.rpc is None:
			raise SyntaxError("Usage: %s  -c routing,key …" % (self.name,))
		d = {}
		while args:
			i = args[-1].find('=')
			if i < 1:
				break
			w = args.pop()
			k = w[:i]
			s = w[i+1:]
			try:
				s = eval(s)
			except ValueError:
				pass
			r_attr(d,k, value=s)
		if args:
			d['args'] = args

		if self.options.uuid:
			d['_dest'] = self.options.uuid

		amqp = await self.root._get_amqp()
		if self.options.timeout:
			d['timeout'] = self.options.timeout
		if self._alert:
			def cb(msg):
				pprint(msg.data)
			res = amqp.alert(self.options.rpc, callback=cb, **d)
		else:
			res = amqp.rpc(self.options.rpc, **d)
		if self.options.timeout:
			res = asyncio.wait_for(res, self.options.timeout, loop=self.root.loop)
		try:
			res = await res
		except asyncio.TimeoutError:
			print("-timed out", file=self.stdout)
			res = "Timeout"
		if not self._alert:
			from yaml import dump
			dump(res, stream=self.stdout)

class AlertCommand(CmdCommand):
	name = "alert"
	_alert = True
	description = """\
Send an arbitrary message to the bus.

Arguments:
* routing key
* any number of name=value pairs
"""

class ListCommand(Command):
	name = "list"
	summary = "Retrieve MoaT.2 data"
	description = """\
This command sends a "list" request to the MoaT.v2 daemon and prints the
result(ing mess).

"""

	def addOptions(self):
		self.parser.add_option('-u','--uuid',
			action="store", dest="uuid",
			help="Query this UUID directly")
		self.parser.add_option('-t','--timeout',
			action="store", dest="timeout", type="int", default=60,
			help="Command timeout")

	async def do(self,args):
		def collapse(x):
			if not isinstance(x,(tuple,list)):
				return str(x)
			return " ".join((collapse(xx) for xx in x))
		amqp = await self.root._get_amqp()

		d={}
		if self.options.uuid:
			d['_dest'] = self.options.uuid

		res = amqp.rpc("moat.list",args=args, **d)
		if self.options.timeout:
			res = asyncio.wait_for(res, self.options.timeout, loop=self.root.loop)
		try:
			res = await res
		except asyncio.TimeoutError:
			print("-timeout")
		else:
			for x in res:
				print(collapse(x))

class HostsCommand(Command):
	name = "hosts"
	summary = "Retrieve MoaT systems"
	description = """\
Enumerate the MoaT systems on the bus.

"""

	def addOptions(self):
		self.parser.add_option('-u','--uuid',
			action="store", dest="uuid",
			help="Query this UUID only")
		self.parser.add_option('-a','--app',
			action="store", dest="app",
			help="limit the list to this app")
		self.parser.add_option('-t','--timeout',
			action="store", dest="timeout", type="int", default=2,
			help="Enumeration timeout")

	async def do(self,args):
		await self.setup()
		amqp = self.root.amqp
		todo = set()

		def cb(data,uuid=None):
			if uuid is None:
				uuid = data['uuid']

			def d(f):
				todo.remove(f)
				try:
					res = f.result()
				except asyncio.CancelledError:
					if self.root.verbose > 1:
						dump(dict(uuid=uuid,error="no answer"), stream=self.stdout)
						print("---",file=self.stdout)
					else:
						print("No answer",uuid)
				except Exception:
					print_exc()
				else:
					if self.root.verbose > 1:
						dump(dict(res), stream=self.stdout)
						print("---",file=self.stdout)
					else:
						print(res['uuid'],res['app'], sep='\t', file=self.stdout)
			f = amqp.rpc('qbroker.ping', _dest=uuid, _timeout=self.options.timeout)
			if self.options.timeout > 0:
				f = asyncio.wait_for(f,self.options.timeout, loop=self.root.loop)
			f = asyncio.ensure_future(f, loop=self.root.loop)

			f.add_done_callback(d)
			todo.add(f)

		if self.options.uuid:
			cb(None,self.options.uuid)
			for t in list(todo): # only one
				await t
		else:
			d = {}
			if self.options.app:
				d['app'] = self.options.app
			await amqp.alert("qbroker.ping",callback=cb,call_conv=CC_DATA, timeout=self.options.timeout, _data=d)
			for t in list(todo):
				t.cancel()

class EventCommand(Command):
	name = "event"
	summary = "Monitor MoaTv2 events"
	description = """\
Report events emitted by MoaTv2, until interrupted.
"""

	async def do(self,args):
		async def coll(msg):
			if msg.data.get('deprecated',False):
				return
			if msg.data.get('event',('',))[0] == 'wait':
				return
			dump(msg, stream=self.stdout)
			print('---')

		await self.setup()
		amqp = self.root.amqp
		if not args:
			args = '#'
		else:
			args = '.'.join(args)
		await amqp.register_alert_async(args,coll, call_conv=CC_MSG)
		while True:
			await asyncio.sleep(100)

class BrokerCommand(SubCommand):
	name = "broker"
	summary = "Talk to the message broker"
	description = """\
Commands to directly access the message broker.

Use with caution.
"""

	# process in order
	subCommandClasses = [
		AlertCommand,
		CmdCommand,
		ListCommand,
		EventCommand,
		HostsCommand,
	]



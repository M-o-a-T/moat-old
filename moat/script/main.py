#!/usr/bin/python3
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

from moat.script import Command, CommandExited, CommandError
import glob
import sys
import os
from etctree.util import from_yaml
import yaml
from moat.cmd import commands as moat_commands
from dabroker.unit import make_unit, DEFAULT_CONFIG
from etctree import client
import asyncio
import socket

DEFAULT_CFG="/etc/moat.cfg"

def r_update(a,b):
	for k,v in b.items():
		if not hasattr(v,'items'):
			a[k] = v
		else:
			if k not in a:
				a[k] = {}
			r_update(a[k],v)

class Moat(Command):
	usage = "[MoaT options] %command"
	summary = "MoaT utility"
	description = """
This is the main MoaT command line processor.

If the config file is not specified with --config, the current directory will be
searched for *.cfg files.  If there is only one, that will be used;
otherwise you will be asked to specify. If there is none, /etc/moat.cfg
will be used. If that doesn't exist either, this command fails.

You can load more than one config file.
"""
	subCommandClasses = list(moat_commands())

	cfg = None
	verbose = None
	_etcd = None

	def addOptions(self):
		self.parser.add_option('--no-default-config',
			action="store_true", dest="no_default",
			help="do not apply the hard-coded default configuration")
		self.parser.add_option('-c', '--config',
			action="append", dest="files",
			help="config file(s) to read (wildcards are OK)")
		self.parser.add_option('-o', '--opt',
			action="append", dest="opts",
			help="option to override (use 'path.to.opt.name=value')")
		self.parser.add_option('-v', '--verbose',
			action="count", dest="verbose", default=1,
			help="increase verbosity")
		self.parser.add_option('-q', '--quiet',
			action="store_const", dest="verbose", const=0,
			help="turn off verbosity")
		self.parser.add_option('-a', '--app',
			action="store", dest="app",
			help="application name. Default is the reversed FQDN.")

	def sync(self,cmd):
		cmd = asyncio.async(cmd, loop=self.loop)
		return self.loop.run_until_complete(cmd)
		
	def handleOptions(self, opts):
		self.verbose = opts.verbose
		self.loop = asyncio.get_event_loop()

		paths = []
		if opts.files:
			for f in opts.files:
				paths.extend(glob.glob(f))

		if not paths:
			if os.path.exists(DEFAULT_CFG):
				paths.append(DEFAULT_CFG)

		self.cfg = {}
		if not opts.no_default:
			r_update(self.cfg.setdefault('config',{}), DEFAULT_CONFIG)
		for p in paths:
			with open(p) as f:
				cfg = yaml.safe_load(f)
				r_update(self.cfg, cfg)
		if opts.opts:
			for o in opts.opts:
				k,v = o.split('=',1)
				oc = None
				c = self.cfg
				for kk in k.split('.'):
					oc = c
					ok = kk
					c = c.setdefault(kk,{})
				oc[ok] = v

		self.app = self.cfg['config'].get('app',None)
		if self.app is None:
			# Rather than enumerate IP addresses, this is the quick&only-somewhat-dirty way
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(('8.8.8.8', 53)) # connecting to a UDP address doesn't send packets
			addr = s.getsockname()[0]
			s.close()
			addr = socket.getfqdn(addr).split('.')
			if len(addr) < 3:
				raise CommandError("You need to fix your FQDN ('%s'), or use the '-a' option." % ".".join(addr))
			addr.reverse()
			self.cfg['config']['app'] = self.app = ".".join(addr)

#		if 'specific' in kw and appname is not None:
#			s = kw['specific']
#			while True:
#				try:
#					tree = s[appname]['config']
#				except KeyError:
#					pass
#				else:
#					r_default(kw['config'],tree)
#				try:
#					appname = appname[appname.index('.'):]
#				except ValueError:
#					break

		if self.verbose > 2:
			print("App name:",self.app)

	async def setup(self):
		"""Once running in async mode, get our basic config loaded"""
		if self.etcd is None:
			self.etcd = await self._get_etcd()
		if self.amqp is None:
			self.amqp = await self._get_amqp()

	def _get_etcd(self):
		return client(self.cfg)
	_get_etcd._is_coroutine = True

	async def _get_amqp(self):
		res = await make_unit(self.cfg)
		t = await res.tree("/config", static=True)
		cfg = {'config':{}}
		r_update(cfg['config'],t)
		r_update(cfg,self.cfg)
		return res


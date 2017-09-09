#!/usr/bin/python3
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

import glob
import sys
import os
from etcd_tree.util import from_yaml
import yaml
import asyncio
import socket

from qbroker.unit import make_unit, DEFAULT_CONFIG as QBROKER_DEFAULT_CONFIG

from moat.script import SubCommand, CommandError
from moat.cmd import commands as moat_commands
from moat.util import OverlayDict
from moat.types import TYPEDEF_DIR
from moat.task.reg import Reg

import logging
logger = logging.getLogger(__name__)

DEFAULT_CFG="/etc/moat/moat.cfg"

DEFAULT_CONFIG = dict(
	testing=False,
	run={
		'ttl':30,
		'refresh':2,
		'retry':1,
		'max-retry':600,
		'restart':2,
		'one-shot':False,
	}
)

def r_update(a,b):
	for k,v in b.items():
		if not hasattr(v,'items'):
			a[k] = v
		else:
			if k not in a:
				a[k] = {}
			r_update(a[k],v)

class Moat(SubCommand):
	usage = "[MoaT options] command [args …]"
	summary = "MoaT utility"
	description = """
This is the main MoaT command line processor.

If the config file is not specified with --config, the current directory will be
searched for *.cfg files.  If there is only one, that will be used;
otherwise you will be asked to specify. If there is none, the content of
the MOAT_CFG environment variable or /etc/moat.cfg will be used.
If that doesn't exist either, this command fails.

You can load more than one config file.
"""
	subCommandClasses = list(moat_commands())

	cfg = None
	verbose = None
	etcd = None
	amqp = None
	tree = None
	loop = None
	logged = False
	etc_cfg = None
	_coro = False
	_types = None
	reg = None

	def __init__(self,*a,loop=None,**kw):
		super().__init__(*a,**kw)
		self.loop = loop if loop is not None else asyncio.get_event_loop()
		self._coro = (loop is not None)
		self._tree_lock = asyncio.Lock(loop=self.loop)

	async def parse(self, argv):
		logger.debug("Startup: %s", argv)
		self.logged = False
		self.reg = Reg()

		try:
			res = await super().parse(argv)
		finally:
			await self.finish()
		return res

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
		self.parser.add_option('-L', '--log-to',
			action="store", dest="logto",
			help="write the log to this file")
		self.parser.add_option('-v', '--verbose',
			action="count", dest="verbose", default=1,
			help="increase verbosity")
		self.parser.add_option('-q', '--quiet',
			action="store_const", dest="verbose", const=0,
			help="turn off verbosity")
		self.parser.add_option('-a', '--app',
			action="store", dest="app",
			help="application name. Default is the reversed FQDN.")

	async def finish(self):
		logger.debug("Closing %s",self)
		e,self.reg = self.reg,None
		if e is not None:
			try:
				await e.free()
			except NameError:
				pass # GC
			except Exception as exc:
				logger.exception("Closing Registry")
		e,self.amqp = self.amqp,None
		if e is not None:
			try:
				await e.stop()
			except NameError:
				pass # GC
			except Exception as exc:
				logger.exception("Closing AMQP")

		e,self.etc_cfg = self.etc_cfg,None
		if e is not None:
			try:
				await e.close()
			except NameError:
				pass # GC
			except Exception as exc:
				logger.exception("Closing etcd cfg tree")

		e,self.tree = self.tree,None
		if e is not None:
			try:
				await e.close()
			except NameError:
				pass # GC
			except Exception as exc:
				logger.exception("Closing etcd tree")

		e,self.etcd = self.etcd,None
		if e is not None:
			try:
				e.close()
			except NameError:
				pass # GC
			except Exception as exc:
				logger.exception("Closing etcd connection")

		await super().finish()
		logger.debug("Closed %s",self)

	def handleOptions(self):
		opts = self.options
		self.verbose = opts.verbose

		paths = []
		if opts.files:
			for f in opts.files:
				paths.extend(glob.glob(f))

		if not paths: # pragma: no cover ## not while testing!
			if 'MOAT_CFG' in os.environ:
				paths.append(os.environ['MOAT_CFG'])
			elif os.path.exists(DEFAULT_CFG):
				paths.append(DEFAULT_CFG)

		self.cfg = {'config':{}}
		if not opts.no_default:
			r_update(self.cfg['config'], DEFAULT_CONFIG)
			r_update(self.cfg['config'], QBROKER_DEFAULT_CONFIG)
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
		#logging.basicConfig(stream=logfile,level=(logging.ERROR,logging.WARNING,logging.INFO,logging.INFO,logging.DEBUG)[min(self.verbose,4)])
		lcfg = self.cfg['config'].setdefault('logging',{'version':1})
		hd = lcfg.setdefault('root',{}).setdefault('handlers',[])
		if opts.logto:
			if 'logfile' not in hd:
				hd.append('logfile')
			lh = lcfg['handlers'].setdefault('logfile',
				{'level':'logging.DEBUG',
				 'formatter':'std',
				})
			lh['class'] = 'logging.FileHandler'
			lh['filename'] = opts.logto
		fmt = lcfg.setdefault('formatters',{})
		fmt.setdefault('std', {'format': '%(levelname)s:%(name)s:%(message)s'})
		fmt.setdefault('stderr', {'format': '%(message)s'})

		if opts.verbose:
			if 'stderr' not in hd:
				hd.append('stderr')
		else:
			if 'stderr' in hd:
				hd.remove('stderr')
		lh = lcfg.setdefault('handlers',{}).setdefault('stderr', { 'formatter':'stderr' })
		lh['class'] = 'logging.StreamHandler'
		lh['stream'] = sys.stderr
		lh['level'] = ('ERROR','ERROR','WARNING','INFO','INFO','DEBUG')[min(self.verbose,5)]

		from logging.config import dictConfig
		lcfg['disable_existing_loggers'] = False
		dictConfig(lcfg)
		logging.captureWarnings(True)

		self.app = self.cfg['config'].get('app',None)
		
		# Rather than enumerate IP addresses, this is the quick&only-somewhat-dirty way
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 53)) # connecting to a UDP address doesn't send packets
		addr = s.getsockname()[0]
		s.close()
		addr = socket.getfqdn(addr)
		addr = addr.split('.')
		if len(addr) < 3: # pragma: no cover
			raise CommandError("You need to fix your FQDN ('%s'), or use the '-a' option." % ".".join(addr))
		#addr.reverse()
		self.host = ".".join(addr)

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

	@property
	def path(self):
		return "cmd"

	async def setup(self, dest=None, prefix=None):
		"""
			Attach to etcd and amqp, get etcd tree.

			Also, set etcd+amqp+tree attributes of `dest` parameter, if given.
			"""
		if self.etcd is None:
			await self._get_etcd()
		if self.amqp is None:
			await self._get_amqp(prefix=prefix)
		if dest not in (None,self):
			dest.etcd = self.etcd
			dest.amqp = self.amqp
			dest.tree = self.tree

	async def _get_tree(self):
		"""\
			Returns the "main" etcd tree (lazily loaded).

			Also, populates .types with etcd's TYPEDEF_DIR.
			"""
		async with self._tree_lock:
			if self.tree is None:
				etc = await self._get_etcd()

				from moat.types.etcd import MoatRoot
				self.tree = await etc.tree('/', root_cls=MoatRoot, immediate=None)
				self.types = await self.tree.subdir(TYPEDEF_DIR,recursive=True)
		return self.tree

	async def _get_etcd(self):
		"""\
			Connect to etcd.

			Also, underlays the current configuration with whatever is in etcd.
			"""
		if self.etcd is not None:
			return self.etcd
		from etcd_tree import client
		from etcd_tree.etcd import EtcTypes
		self._types = types = EtcTypes()

		self.etcd = etc = await client(self.cfg, loop=self.loop)
		self.etc_cfg = await etc.tree("/config", types=types.step('config'))
		self.cfg = OverlayDict(self.cfg,{'config': self.etc_cfg})
		return etc

	async def _get_amqp(self, prefix=None):
		if self.amqp is not None:
			return self.amqp
		p = self.cfg['config'].get('app','moat')
		if prefix:
			p += '.'+prefix
		self.amqp = res = await make_unit(p, loop=self.loop, amqp=self.cfg['config']['amqp'])
		return res

	def load(self, subsys,name):
		"""
			Return the class for etcd's /SUBSYS/NAME, assuming that SUBSYS
			is 'bus' or 'device'.
			"""
		return self.tree.lookup('meta','module', name,subsys).code


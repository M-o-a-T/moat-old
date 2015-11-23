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

"""List of known Tasks"""

import os
from moat.script import Command, CommandError
from etctree.util import from_etcd
import aioetcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['ShowCommand']

class ConfigCommand(Command):
	name = "config"
	summary = "View configuration data"""
	description = """\
Show the current config data.

With arguments, show only these.
"""

	def do(self,args):
		from yaml import safe_dump
		if args:
			try:
				for n,a in enumerate(args):
					if n:
						print("---", file=self.stdout)
					c = self.root.cfg
					for aa in a.split('.'):
						c = c[aa]
					safe_dump(c, stream=self.stdout)
			except KeyError:
				raise CommandError("Key %s does not exist"%(repr(a),))
		else:
			safe_dump(self.root.cfg, stream=self.stdout)

class EtcdCommand(Command):
	name = "etcd"
	summary = "View etcd data"""
	description = """\
Show the current etcd contents.

With arguments, show only these subtrees.
"""

	def addOptions(self):
		self.parser.add_option('-d','--dump',
            action="store_true", dest="dump",
            help="show internal details")
		self.parser.add_option('-m','--modstamp',
            action="store_true", dest="mod",
            help="return the entry's modification number")

	def handleOptions(self):
		self.dump = self.options.dump
		self.mod = self.options.mod

	def do(self,args):
		from yaml import safe_dump
		retval = 0
		etc = self.root.sync(self.root._get_etcd())
		if args:
			for n,a in enumerate(args):
				if n:
					print("---", file=self.stdout)
				a = a.replace('.','/')
				try:
					if self.mod:
						res = self.root.sync(etc.get('/'+a))
						print(res.modifiedIndex, file=self.stdout)
					else:
						safe_dump(self.root.sync(from_etcd(etc,'/'+a, dump=self.dump)), stream=self.stdout)
				except etcd.EtcdKeyNotFound:
					logger.error("key not present: %s",a)
					retval = 1

		else:
			if self.mod:
				res = self.root.sync(etc.get('/'))
				print(res.modifiedIndex, file=self.stdout)
			else:
				safe_dump(self.root.sync(from_etcd(etc, '/', dump=self.dump)), stream=self.stdout)
		return retval

class ShowCommand(Command):
	name = "show"
	summary = "Show various data"""
	description = """\
Show some data.
"""

	subCommandClasses = [EtcdCommand,ConfigCommand]


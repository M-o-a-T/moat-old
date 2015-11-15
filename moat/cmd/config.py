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
import sys
from moat.script import Command, CommandError
from etctree.util import from_etcd

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
			done = False
			for n,a in enumerate(args):
				if n:
					print("---")
				c = self.root.cfg
				for aa in a.split('.'):
					c = c[aa]
				safe_dump(c, stream=sys.stdout)

		else:
			safe_dump(self.root.cfg, stream=sys.stdout)

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

	def handleOptions(self,opts):
		self.dump = opts.dump

	def do(self,args):
		from yaml import safe_dump
		if args:
			done = False
			for n,a in enumerate(args):
				if n:
					print("---")
				a = a.replace('.','/')
				safe_dump(self.root.sync(from_etcd(self.root.etcd,'/'+a, dump=self.dump)), stream=sys.stdout)

		else:
			safe_dump(self.root.sync(from_etcd(self.root.etcd, '/', dump=self.dump)), stream=sys.stdout)

class ShowCommand(Command):
	name = "show"
	summary = "Show various data"""
	description = """\
Show some data.
"""

	subCommandClasses = [EtcdCommand,ConfigCommand]


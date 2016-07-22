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

"""Commands to setup and modify tasks"""

import os
import sys
from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task
from moat.script.util import objects
from moat.task import TASKDEF_DIR
from moat.types import MODULE_DIR
from moat.types.module import BaseModule, modules
from qbroker.util import import_string
from yaml import safe_dump
from etcd_tree import EtcXValue
import aio_etcd as etcd
import asyncio
import types as py_types

import logging
logger = logging.getLogger(__name__)

__all__ = ['ModuleCommand']

class ModuleSetup:
	async def setup(self):
		await super().setup()
		tree = self.root.tree
		return (await tree.subdir(MODULE_DIR))

class ModuleInitCommand(Command,ModuleSetup):
	name = "init"
	summary = "Set up task definitions"
	description = """\
Module declarations are stored in etcd at /meta/module/NAME/FUNCTION.

This command sets up that data. If you mention module or class names
on the command line, they are added, otherwise everything under
'moat.ext.*' is used.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="update existing values")
		self.parser.add_option('-n','--no-tasks',
			action="store_true", dest="no_tasks",
			help="don't add the module's task definitions")

	def handleOptions(self):
		self.force = self.options.force
		self.tasks = not self.options.no_tasks

	async def do(self,args):
		t = await self.setup()
		tree = await self.root._get_tree()
		t2 = await tree.subdir(TASKDEF_DIR)

		if args:
			objs = []
			for a in args:
				m = import_string(a)
				if isinstance(m,py_types.ModuleType):
					try:
						syms = m.__all__
					except AttributeError:
						syms = dir(m)
					n = 0
					for c in syms:
						c = getattr(m,c,None)
						if isinstance(c,type) and issubclass(c,BaseModule) and c.prefix is not None:
							objs.append(c)
							n += 1
					if self.root.verbose > (1 if n else 0):
						print("%s: %s module%s found." % (a,n if n else "no", "" if n==1 else "s"), file=self.stdout)

					if self.tasks:
						n = 0
						for c in objects(m, Task, filter=lambda x:getattr(x,'taskdef',None) is not None):
							await t2.add_task(c, force=self.force)
							n += 1
						if self.root.verbose > (1 if n else 0):
							print("%s: %s command%s found." % (a,n if n else "no", "" if n==1 else "s"), file=self.stdout)

				else:
					if not isinstance(m,BaseModule):
						raise CommandError("%s is not a task"%a)
					objs.append(m)
		else:
			objs = modules()

		tasks = await t.root.subdir(TASKDEF_DIR)
		for obj in objs:
			await t.add_module(obj, force=self.force)
			for ta in obj.task_types():
				await tasks.add_task(ta, force=self.force)
		await t.wait()

class ModuleListCommand(Command,ModuleSetup):
	name = "list"
	summary = "List module definitions"
	description = """\
Module definitions are stored in etcd at /meta/module/NAME/FUNCTION.

This command shows that data.
"""

	async def do(self,args):
		t = await self.setup()
		if args:
			dirs = []
			for a in args:
				tt = t
				try:
					for k in a.split('/'):
						if k:
							tt = tt._get(k)
					dirs.append(tt)
				except KeyError:
					print("Module '%s' not known"%(a,), file=sys.stderr)
		else:
			dirs = (t,)

		async def _pr(tt):
			if isinstance(tt,EtcXValue):
				print('/'.join(tt.path[len(MODULE_DIR):]),tt.value, sep='\t')
			elif 'descr' in tt and not args:
				d = tt['descr']
				print(tt.name,d, sep='\t')
			else:
				for v in tt._values():
					v = await v
					await _pr(v)

		for tt in dirs:
			tt = await tt
			await _pr(tt)

class ModuleDeleteCommand(Command,ModuleSetup):
	name = "delete"
	summary = "Delete module definitions"
	description = """\
Module definitions are stored in etcd at /meta/module/NAME/FUNCTION.

This command deletes (some of) that data.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="not forcing won't do anything")

	async def do(self,args):
		t = await self.setup()
		if args:
			dirs = []
			for a in args:
				tt = t
				try:
					for k in a.split('/'):
						if k:
							tt = tt._get(k)
					dirs.append(tt)
				except KeyError:
					print("Module '%s' not known"%(a,), file=sys.stderr)
		else:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			dirs = (t)

		for k in dirs:
			t = await k
			k = t.path
			rec=None
			while True:
				p = t._parent
				if p is None: break
				p = p()
				if p is None or p is t: break
				try:
					await t.delete(recursive=rec)
				except etcd.EtcdDirNotEmpty:
					break
				if isinstance(t,MoatLoaderDir):
					try:
						t2 = t.root.lookup(*TASKDEF_DIR,self.name)
					except KeyError:
						pass
					else:
						await t2.delete(recursive=True)
				rec=False
				t = p
			if self.root.verbose:
				print("%s: deleted"%'/'.join(k), file=self.stdout)

class ModuleCommand(SubCommand):
	name = "mod"
	summary = "Configure modules"
	description = """\
Commands to set up and admin the list of modules known to MoaT.
"""

	subCommandClasses = [
		ModuleInitCommand,
		ModuleListCommand,
		ModuleDeleteCommand,
	]
	fix = False


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

"""Commands to setup and modify tasks"""

import os
import sys
from moat.script import Command, CommandError
from moat.script.task import Task
from moat.task import tasks
from moat.util import r_dict
from etctree.util import from_etcd
from etctree.etcd import EtcTypes
from dabroker.util import import_string
from ..task import task_var_types
import aioetcd as etcd
import asyncio
import time
import types as py_types

import logging
logger = logging.getLogger(__name__)

__all__ = ['TaskCommand']

class DefSetup:
	async def setup(self):
		await self.root.setup()
		etc = self.root.etcd
		types = EtcTypes()
		task_var_types(types.step('*'))
		t = await etc.tree('/meta/task',types=types)
		return t

class DefInitCommand(Command,DefSetup):
	name = "init"
	summary = "Set up task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/*.

This command sets up that data. If you mention module or class names
on the command line, they are added, otherwise everything under
'moat.task.*' is used.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
            action="store_true", dest="force",
            help="update existing values")

	def handleOptions(self):
		self.force = self.options.force

	async def do_async(self,args):
		t = await self.setup()
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
						if isinstance(c,type) and c is not Task and issubclass(c,Task):
							objs.append(c)
							n += 1
					if self.root.verbose > (1 if n else 0):
						print("%s: %s command%s found." % (a,n if n else "no", "" if n==1 else "s"), file=self.stdout)
				else:
					if not isinstance(m,Task):
						raise CommandError("%s is not a task"%a)
					objs.append(m)
		else:
			objs = tasks()

		for obj in objs:
			d = dict(
				language='python',
				code=obj.__module__+'.'+obj.__name__,
				summary=obj.summary or "? no summary given",
				description=getattr(obj,'description',obj.__doc__)
			)
			if hasattr(obj,'schema'):
				d['data'] = obj.schema
			if obj.name in t:
				if self.force:
					tt = t[obj.name]
					changed = False
					for k,v in d.items():
						if k not in tt:
							if self.root.verbose > 1:
								print("%s: Update %s: %s => %s" % (obj.name,k,tt[k],v), file=self.stdout)
						elif tt[k] != v:
							if self.root.verbose > 1:
								print("%s: Add %s: %s" % (obj.name,k,v), file=self.stdout)
						else:
							continue
						await tt.set(k,v)
						changed = True
					if self.root.verbose:
						print("%s: updated" % obj.name, file=self.stdout)
				elif self.root.verbose > 1:
					print("%s: exists, skipped" % obj.name, file=self.stdout)
				continue
			else:
				if self.root.verbose:
					print("%s: new" % obj.name, file=self.stdout)
				await t.set(obj.name,d)
		t.wait()

class DefListCommand(Command,DefSetup):
	name = "list"
	summary = "List task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/*.

This command shows that data. If you mention a definition's name,
details are shown in YAML format, else a short list of names is shown.
"""

	def addOptions(self):
		self.parser.add_option('-a','--all',
			action="store_true", dest="all",
			help="show details for all entries")

	async def do_async(self,args):
		t = await self.setup()
		if args:
			if self.options.all:
				raise CommandError("Arguments and '-a' are mutually exclusive")
			args = ((a,t[a]) for a in args)
			verbose = True
		else:
			args = t.items()
			verbose = self.options.all
		if verbose:
			from yaml import safe_dump
			import pdb;pdb.set_trace()
			safe_dump(r_dict(dict(args)), stream=self.stdout)
		else:
			for k,v in args:
				print(k,v['summary'], sep='\t',file=self.stdout)

class DefDeleteCommand(Command,DefSetup):
	name = "delete"
	summary = "Delete task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/*.

This command deletes (some of) that data.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="not forcing won't do anything")

	async def do_async(self,args):
		t = await self.setup()
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = t
		for k in args:
			if k not in t:
				raise CommandError("%s: does not exist"%k)
			if self.root.verbose:
				print("%s: deleted"%k, file=self.stdout)
			await t.delete(k)


class DefParamCommand(Command,DefSetup):
	name = "param"
	summary = "Parameterize task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/*.

This command shows/changes/deletes parameters for that data.

Usage: … param NAME VALUE  -- set
       … param             -- list all
       … param NAME        -- show one
       … param -d NAME     -- delete
"""

	def addOptions(self):
		self.parser.add_option('-d','--delete',
			action="store_true", dest="delete",
			help="delete specific parameters")
		self.parser.add_option('-g','--global',
			action="store_true", dest="is_global",
			help="show global parameters")

	async def do_async(self,args):
		from moat.task import _VARS
		t = await self.setup()
		if self.options.is_global:
			if self.options.delete:
				raise CommandError("You cannot delete global parameters.")
			taskdef = self.root.config['run']
		elif not args:
			if self.options.delete:
				raise CommandError("You cannot delete all parameters.")
			for name,taskdef in t.items():
				for k in _VARS:
					if k in taskdef:
						print(name,k,taskdef[k], sep='\t',file=self.stdout)
			return
		else:
			name = args.pop(0)
			if name not in t:
				raise CommandError("Task definition '%s' is unknown." % name)
			taskdef = t[name]

		if self.options.delete:
			if not args:
				args = _VARS
			for k in args:
				if k in taskdef:
					if self.root.verbose:
						print("%s=%s (deleted)" % (k,taskdef[k]), file=self.stdout)
					await taskdef.delete(k)
		elif len(args) == 1:
			print(taskdef[args[0]], file=self.stdout)
		elif not len(args):
			for k in _VARS:
				if k in taskdef:
					print(k,taskdef[k], sep='\t',file=self.stdout)
		elif len(args)%2:
			raise CommandError("I do not know what to do with an odd number of arguments.")
		else:
			while args:
				k = args.pop(0)
				if k not in _VARS:
					raise CommandError("'%s' is not a valid parameter.")
				v = args.pop(0)
				if self.root.verbose:
					if k in taskdef:
						print("%s=%s (was %s)" % (k,v,taskdef[k]), file=self.stdout)
					else:
						print("%s=%s (new)" % (k,v), file=self.stdout)
				await taskdef.set(k, v)

class DefCommand(Command):
	subCommandClasses = [
		DefInitCommand,
		DefListCommand,
		DefDeleteCommand,
		DefParamCommand,
	]
	name = "def"
	summary = "Define tasks"
	description = """\
Commands to set up and admin the task definitions known to MoaT.
"""

class TaskCommand(Command):
	name = "task"
	summary = "Configure and define tasks"
	description = """\
Commands to set up and admin the task list known to MoaT.
"""

	subCommandClasses = [
		DefCommand,
	]
	fix = False

	def do(self,args):
		if self.root.cfg['config'].get('testing',False):
			print("NOTE: this is a test configuration.", file=sys.stderr)
		else: # pragma: no cover ## not doing the real thing here
			print("WARNING: this is NOT a test.", file=sys.stderr)
			time.sleep(3)

		res = 0
		for c in self.subCommandClasses:
			if c.summary is None:
				continue
			if self.root.verbose > 1:
				print("Checking:",c.name)
			c = c(parent=self)
			try:
				res |= (c.do(args) or 0)
			except Exception as exc: # pragma: no cover
				if self.root.verbose > 1:
					import traceback
					traceback.print_exc(file=sys.stderr)
					return 9
				raise CommandError("%s failed: %s" % (c.name,repr(exc)))
		if self.root.verbose:
			print("All tests done.")
		return res


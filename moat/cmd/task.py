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
from ..task import task_var_types, TASK_DIR,TASKDEF_DIR,TASK,TASKDEF
from yaml import safe_dump
import aioetcd as etcd
import asyncio
import time
import types as py_types

import logging
logger = logging.getLogger(__name__)

__all__ = ['TaskCommand']

class DefSetup:
	async def setup(self, meta=False):
		await self.root.setup()
		etc = self.root.etcd
		types = EtcTypes()
		if meta:
			task_var_types(types.step('**').step(TASKDEF))
			t = await etc.tree(TASKDEF_DIR,types=types)
		else:
			task_var_types(types.step('**').step(TASK))
			t = await etc.tree(TASK_DIR,types=types)
		return t

class DefInitCommand(Command,DefSetup):
	name = "init"
	summary = "Set up task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/**/:taskdef.

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
		t = await self.setup(meta=True)
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
			tt = await t.subdir(obj.name,name=TASKDEF, create=True)
			if 'language' in tt: ## mandatory
				if self.force:
					changed = False
					for k,v in d.items():
						if k not in tt:
							if self.root.verbose > 1:
								print("%s: Add %s: %s" % (obj.name,k,v), file=self.stdout)
						elif tt[k] != v:
							if self.root.verbose > 1:
								print("%s: Update %s: %s => %s" % (obj.name,k,tt[k],v), file=self.stdout)
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
				await tt.update(d)
		await t.wait()

class DefListCommand(Command,DefSetup):
	name = "list"
	summary = "List task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/**/:taskdef.

This command shows that data. If you mention a definition's name,
details are shown in YAML format, else a short list of names is shown.
"""

	def addOptions(self):
		self.parser.add_option('-a','--all',
			action="store_true", dest="all",
			help="show details for all entries")

	async def do_async(self,args):
		t = await self.setup(meta=True)
		if args:
			if self.options.all:
				raise CommandError("Arguments and '-a' are mutually exclusive")
			dirs = []
			for a in args:
				dirs.append(await t.subdir(a))
			verbose = True
		else:
			dirs = [t]
			verbose = self.options.all
		for tt in dirs:
			for task in tt.tagged(TASKDEF):
				path = task.path[len(TASKDEF_DIR)+1:-(len(TASKDEF)+1)]
				if verbose:
					safe_dump({path: r_dict(dict(task))}, stream=self.stdout)
				else:
					print(path,task['summary'], sep='\t',file=self.stdout)

class DefDeleteCommand(Command,DefSetup):
	name = "delete"
	summary = "Delete task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/**/:taskdef.

This command deletes (some of) that data.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="not forcing won't do anything")

	async def do_async(self,args):
		t = await self.setup(meta=True)
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
Task definitions are stored in etcd at /meta/task/**/:taskdef.

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
		t = await self.setup(meta=True)
		if self.options.is_global:
			if self.options.delete:
				raise CommandError("You cannot delete global parameters.")
			taskdef = self.root.etc_cfg['run']
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
			try:
				taskdef = await t.subdir(name+'/'+TASKDEF)
			except KeyError:
				raise CommandError("Task definition '%s' is unknown." % name)

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

class ListCommand(Command,DefSetup):
	name = "list"
	summary = "List tasks"
	description = """\
Tasks are stored in etcd at /task/**/:task.

This command shows that data. If you mention a task's path,
details are shown in YAML format, else a short list of tasks is shown.
"""

	def addOptions(self):
		self.parser.add_option('-a','--all',
			action="store_true", dest="all",
			help="show details for all entries")

	async def do_async(self,args):
		t = await self.setup(meta=False)
		if args:
			if self.options.all:
				raise CommandError("Arguments and '-a' are mutually exclusive")
			dirs = []
			for a in args:
				dirs.append(await t.subdir(a))
			verbose = True
		else:
			dirs = [t]
			verbose = self.options.all
		for tt in dirs:
			for task in tt.tagged(TASK):
				path = task.path[len(TASK_DIR)+1:-(len(TASK)+1)]
				if verbose:
					safe_dump({path:r_dict(dict(task))}, stream=self.stdout)
				else:
					name = task['name']
					if name == path:
						name = "-"
					print(path,name,task['descr'], sep='\t',file=self.stdout)

class _AddUpdate:
	"""Mix-in to add or update a task (too much)"""
	async def do_async(self,args):
		try:
			data = {}
			taskdefpath=""
			name=""
			p=0

			taskpath = args[p].rstrip('/').lstrip('/')
			if taskpath == "":
				raise CommandError("Empty task path?")
			if taskpath.endswith(TASK):
				raise CommandError("Don't add the tag")
			p+=1

			if not self._update:
				taskdefpath = args[p].rstrip('/').lstrip('/')
				if taskdefpath == "":
					raise CommandError("Empty task definition path?")
				if taskdefpath.endswith(TASKDEF):
					raise CommandError("Don't add the tag")
				p+=1
			while p < len(args):
				try:
					k,v = args[p].split('=')
				except ValueError:
					break
				p += 1
				if k == "name":
					name = v
				else:
					data[k] = v
			if not self._update:
				args[p] # raises IndexError if nothing is left
			descr = "".join(args[p:])
		except IndexError:
			raise CommandError("Missing command parameters")
		t = await self.setup(meta=False)
		if not self._update:
			try:
				td = await self.setup(meta=True)
				taskdef = await td.subdir(taskdefpath,name=TASKDEF, create=False)
			except KeyError:
				raise CommandError("Taskdef '%s' not found" % taskdefpath)

		try:
			task = await t.subdir(taskpath,name=TASK, create=not self._update)
		except KeyError:
			raise CommandError("Task '%s' not found. (Use its path, not the name?)" % taskpath)
		if not self._update:
			await task.set('task', taskdefpath, sync=False)
			if not name:
				name = taskpath
		if name:
			await task.set('name', name, sync=False)
		if descr:
			await task.set('descr', descr, sync=False)
		if data:
			d = await task.subdir('data', create=True)
			for k,v in data.items():
				if v == "":
					try:
						await d.delete(k, sync=False)
					except KeyError:
						pass
				else:
					await d.set(k,v, sync=False)
			

class AddCommand(_AddUpdate,Command,DefSetup):
	name = "add"
	summary = "add a task"
	description = """\
Create a new task.

Arguments:

* the new task's path (must not exist)

* the task definition's path (must exist)

* data=value parameters (job-specific, optional)

* a descriptive name (not optional)

"""
	_update = False


class UpdateCommand(_AddUpdate,Command,DefSetup):
	name = "change"
	summary = "change a task"
	description = """\
Create a new task.

Arguments:

* the task's path (required)

* data=value entries (deletes the key if value is empty)

* a descriptive name (optional, to update)

"""
	_update = True


class DeleteCommand(Command,DefSetup):
	name = "delete"
	summary = "Delete a task"
	description = """\
Tasks are stored in etcd at /task/**/:task.

This command deletes one of these entries.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="not forcing won't do anything")

	async def do_async(self,args):
		t = await self.setup(meta=False)
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = t
		for k in args:
			try:
				task = await t.subdir(k,name=TASK, create=False)
			except KeyError:
				raise CommandError("%s: does not exist"%k)
			if self.root.verbose:
				print("%s: deleted"%k, file=self.stdout)
			await task.delete()


class TaskCommand(Command):
	name = "task"
	summary = "Configure and define tasks"
	description = """\
Commands to set up and admin the task list known to MoaT.
"""

	subCommandClasses = [
		DefCommand,
		AddCommand,
		UpdateCommand,
		ListCommand,
		DeleteCommand,
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


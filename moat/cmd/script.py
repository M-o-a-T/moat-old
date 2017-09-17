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

"""Commands to setup and modify scripts"""

import asyncio
import os
import sys
import time
import types as py_types
from contextlib import suppress
from datetime import datetime
from yaml import dump

from qbroker.util import import_string
from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task
from moat.task import TASK,TASK_DIR, SCRIPT_DIR,SCRIPT
from moat.types.module import BaseModule
from moat.util import r_dict,r_show

import aio_etcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['TaskCommand']

class DefSetup:
	async def setup(self, meta=False):
		if meta:
			self.DIR=SCRIPT_DIR
		else:
			self.DIR=TASK_DIR
		await super().setup()
		etc = self.root.etcd
		tree = await self.root._get_tree()
		t = await tree.subdir(self.DIR)
		return t

class DefListCommand(DefSetup,Command):
	name = "list"
	summary = "List scripts"
	description = """\
Scripts are stored in etcd at /meta/script/**/:code.

This command shows that data. If you mention a script's name,
details are shown in YAML format, else a short list of names is shown.
"""

	def addOptions(self):
		self.parser.add_option('-a','--all',
			action="store_true", dest="all",
			help="show details for all entries")

	async def do(self,args):
		t = await self.setup(meta=True)
		if args:
			if self.options.all:
				raise CommandError("Arguments and '-a' are mutually exclusive")
			dirs = []
			for a in args:
				dirs.append(await t.subdir(a, create=False))
			verbose = True
		else:
			dirs = [t]
			verbose = self.options.all
		for tt in dirs:
			async for task in tt.tagged(TASKDEF):
				path = task.path[len(TASKDEF_DIR):-1]
				if verbose:
					dump({path: r_dict(dict(task))}, stream=self.stdout)
				else:
					print('/'.join(path),task.get('summary',task.get('descr','??')), sep='\t',file=self.stdout)

class DefGetCommand(DefSetup,Command):
	name = "get"
	summary = "retrieve a scripts"
	description = """\
Scripts are stored in etcd at /meta/script/**/:code.

This command prints a single script to standard output.
"""

	def addOptions(self):
		self.parser.add_option('-o','--old',
			action="store_true", dest="old",
			help="show the script's previous version")
		self.parser.add_option('-n','--new',
			action="store_true", dest="new",
			help="show the script's next (i.e. broken) version")

	async def do(self,args):
		if self.options.old and self.options.new:
			raise SyntaxError("You can't use --old and --new at the same time")
		if len(args) != 1:
			raise SyntaxError("Usage: … get path/to/script")

		t = await self.setup(meta=True)
		sc = t.lookup(args[0])
		sc = await sc.lookup(SCRIPT)
		sys.stdout.write(sc['old_code' if self.options.old else 'new_code' if self.options.new else 'code'])

class DefDeleteCommand(DefSetup,Command):
	name = "delete"
	summary = "Delete a script"
	description = """\
Scripts are stored in etcd at /meta/script/**/:code.

This command deletes a script, provided it's not used anywhere.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="delete even if in use")

	async def do(self,args):
		td = await self.setup(meta=True)
		if not args:
			raise CommandError("You can't delete everything.")
		for k in args:
			t = await td.subdir(k,name=TASKDEF, create=False)
			if self.root.verbose:
				print("%s: deleted"%k, file=self.stdout)
			rec = True
			while True:
				p = t._parent
				if p is None: break
				p = p()
				if p is None or p is t: break
				try:
					await t.delete(recursive=rec)
				except etcd.EtcdDirNotEmpty:
					if rec:
						raise
					break
				rec = False
				t = p

class _ParamCommand(DefSetup,Command):
	name = "param"
	# _def = None ## need to override
	from moat.task import _VARS

	@property
	def description(self):
	return """\

Usage: … param NAME %s  -- set
       … param             -- list all
       … param NAME        -- show one
       … param -d NAME     -- delete
""" % ("TYPE " if self._def else "VALUE",)

	def addOptions(self):
		self.parser.add_option('-d','--delete',
			action="store_true", dest="delete",
			help="delete specific parameters")
		if self._def:
			self.parser.add_option('-g','--global',
				action="store_true", dest="is_global",
				help="show global parameters")

	async def do(self,args):
		t = await self.setup(meta=self._def)
		if self._def and self.options.is_global:
			if self.options.delete:
				raise CommandError("You cannot delete global parameters.")
			data = self.root.etc_cfg['run']
		elif not args:
			if self.options.delete:
				raise CommandError("You cannot delete all parameters.")

			async for task in t.tagged(self.TAG,depth=0):
				path = task.path[len(self.DIR):-1]
				for k in self._VARS:
					if k in task:
						print('/'.join(path),k,task[k], sep='\t',file=self.stdout)
			return
		else:
			name = args.pop(0)
			try:
				data = await t.subdir(name, name=self.TAG, create=None if self._make else False)
			except KeyError:
				raise CommandError("Task definition '%s' is unknown." % name)

		if self.options.delete:
			if not args:
				args = self._VARS
			for k in args:
				if k in data:
					if self.root.verbose:
						print("%s=%s (deleted)" % (k,data[k]), file=self.stdout)
					await data.delete(k)
		elif len(args) == 1 and '=' not in args[0]:
			print(data[args[0]], file=self.stdout)
		elif not len(args):
			for k in self._VARS:
				if k in data:
					print(k,data[k], sep='\t',file=self.stdout)
		else:
			while args:
				k = args.pop(0)
				try:
					k,v = k.split('=',1)
				except ValueError:
					if k not in self._VARS:
						raise CommandError("'%s' is not a valid parameter."%k)
					print(k,data.get(k,'-'), sep='\t',file=self.stdout)
				else:
					if k not in self._VARS:
						raise CommandError("'%s' is not a valid parameter."%k)
					if self.root.verbose:
						if k not in data:
							print("%s=%s (new)" % (k,v), file=self.stdout)
						elif str(data[k]) == v:
							print("%s=%s (unchanged)" % (k,v), file=self.stdout)
						else:
							print("%s=%s (was %s)" % (k,v,data[k]), file=self.stdout)
					await data.set(k, v, ext=True)

class DefParamCommand(_ParamCommand):
	_def = True
	DIR=TASKDEF_DIR
	TAG=TASKDEF
	summary = "Parameterize task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/**/:taskdef.
""" + _ParamCommand.description

class ParamCommand(_ParamCommand):
	_def = False
	DIR=TASK_DIR
	TAG=TASK
	summary = "Parameterize tasks"
	description = """\
Tasks are stored in etcd at /task/**/:task.
""" + _ParamCommand.description

class DefCommand(SubCommand):
	subCommandClasses = [
		DefInitCommand,
		DefListCommand,
		DefGetCommand,
		DefDeleteCommand,
		DefParamCommand,
	]
	name = "def"
	summary = "Define scripts"
	description = """\
Commands to set up and admin the scripts known to MoaT.
"""

class ListCommand(DefSetup,Command):
	name = "list"
	summary = "List tasks for scripts"
	description = """\
This command shows tasks which use a given script.
"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
			action="count", dest="this", default=0,
			help="Show the given job only (-tt for jobs one level below, etc.)")

	async def do(self,args):
		t = await self.setup(meta=True)
		if args:
			dirs = []
			for a in args:
				try:
					dirs.append(await t.subdir(a, create=False))
				except KeyError:
					raise CommandError("'%s' does not exist"%(a,))
		else:
			dirs = [t]
		for tt in dirs:
			async for script in tt.tagged(SCRIPT, depth=self.options.this):
				for task in script['tasks'].values():
					task = await task.task
					path = task.path[len(TASK_DIR):-1]
					if self.root.verbose == 2:
						print('*','/'.join(path), sep='\t',file=self.stdout)
						for k,v in r_show(task,''):
							print(k,v, sep='\t',file=self.stdout)

					elif self.root.verbose > 1:
						dump({'/'.join(path):r_dict(dict(task))}, stream=self.stdout)
					else:
						path = '/'.join(path)
						name = task.get('name','-')
						if name == path:
							name = "-"
						print(path,name,task.get('descr','-'), sep='\t',file=self.stdout)

class _AddUpdate:
	"""Mix-in to add or update a script (too much)"""

	async def do(self,args):
		try:
			data = {}
			scriptdefpath=""
			name=""
			p=0

			scriptpath = args[p].rstrip('/').lstrip('/')
			if scriptpath == "":
				raise CommandError("Empty script path?")
			if scriptpath[0] == ':' or '/:' in scriptpath:
				raise CommandError("Don't add the tag")
			p+=1

			if not self._update:
				scriptdefpath = args[p].rstrip('/').lstrip('/')
				if scriptdefpath == "":
					raise CommandError("Empty script definition path?")
				if scriptdefpath[0] == ':' or '/:' in scriptdefpath:
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
			descr = " ".join(args[p:])
		except IndexError:
			raise CommandError("Missing command parameters")
		t = await self.setup(meta=False)
		if not self._update:
			try:
				td = await self.setup(meta=True)
				scriptdef = await td.subdir(scriptdefpath,name=SCRIPTDEF, create=False)
			except KeyError:
				raise CommandError("Taskdef '%s' not found" % scriptdefpath)

		try:
			script = await t.subdir(scriptpath,name=SCRIPT, create=not self._update)
		except KeyError:
			raise CommandError("Task '%s' not found. (Use its path, not the name?)" % scriptpath)
		if not self._update:
			await script.set('scriptdef', scriptdefpath, sync=False)
		p = self.options.parent
		if p is not None:
			if p == '-':
				with suppress(KeyError):
					await script.delete('parent', sync=False)
			else:
				await script.set('parent', p, sync=False)

		if name:
			await script.set('name', name, sync=False)
		if descr:
			await script.set('descr', descr, sync=False)
		if data:
			d = await script.subdir('data', create=None)
			for k,v in data.items():
				if v == "":
					try:
						await d.delete(k, sync=False)
					except KeyError:
						pass
				else:
					await d.set(k,v, sync=False, ext=True)
			

class _AddUpdate:
	"""Mix-in to add or update a script (too much)"""

	async def do(self,args):
		try:
			data = {}
			scriptdefpath=""
			name=""
			p=0

			scriptpath = args[p].rstrip('/').lstrip('/')
			if scriptpath == "":
				raise CommandError("Empty script path?")
			if scriptpath[0] == ':' or '/:' in scriptpath:
				raise CommandError("Don't add the tag")
			p+=1

			if not self._update:
				scriptdefpath = args[p].rstrip('/').lstrip('/')
				if scriptdefpath == "":
					raise CommandError("Empty script definition path?")
				if scriptdefpath[0] == ':' or '/:' in scriptdefpath:
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
			descr = " ".join(args[p:])
		except IndexError:
			raise CommandError("Missing command parameters")
		t = await self.setup(meta=False)
		if not self._update:
			try:
				td = await self.setup(meta=True)
				scriptdef = await td.subdir(scriptdefpath,name=SCRIPTDEF, create=False)
			except KeyError:
				raise CommandError("Taskdef '%s' not found" % scriptdefpath)

		try:
			script = await t.subdir(scriptpath,name=SCRIPT, create=not self._update)
		except KeyError:
			raise CommandError("Task '%s' not found. (Use its path, not the name?)" % scriptpath)
		if not self._update:
			await script.set('scriptdef', scriptdefpath, sync=False)
		p = self.options.parent
		if p is not None:
			if p == '-':
				with suppress(KeyError):
					await script.delete('parent', sync=False)
			else:
				await script.set('parent', p, sync=False)

		if name:
			await script.set('name', name, sync=False)
		if descr:
			await script.set('descr', descr, sync=False)
		if data:
			d = await script.subdir('data', create=None)
			for k,v in data.items():
				if v == "":
					try:
						await d.delete(k, sync=False)
					except KeyError:
						pass
				else:
					await d.set(k,v, sync=False, ext=True)
			

class AddCommand(_AddUpdate,DefSetup,Command):
	name = "add"
	summary = "add a script task"
	description = """\
Create a new task for a script.

Arguments:

* the new task's path (must not exist)

* the script's path (must exist)

* data=value parameters (job-specific, optional)

* a descriptive name (optional)

"""
	_update = False

class UpdateCommand(_AddUpdate,DefSetup,Command):
	name = "change"
	summary = "change a script task"
	description = """\
Update a task for a script.

Arguments:

* the task's path (required)

* data=value entries (deletes the key if value is empty)

* a descriptive name (optional, to update)

"""
	_update = True

from moat.cmd.task import DeleteCommand as TaskDeleteCommand
class DeleteCommand(TaskDeleteCommand):
	def check(self,task):
		if task._get('taskdef').value != 'task/script':
			print("%s: not a script job, not deleted", % self.path[len(TASK_DIR):-1],), file=sys.stderr)
			return False
		return True

class ScriptCommand(SubCommand):
	name = "script"
	summary = "Upload and run scripts"
	description = """\
Commands to set up and run scripts"
"""

	subCommandClasses = [
		DefCommand,
		AddCommand,
		UpdateCommand,
		ParamCommand,
		ListCommand,
		DeleteCommand,
	]
	fix = False


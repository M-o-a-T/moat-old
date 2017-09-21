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
from moat.script.util import _ParamCommand
from moat.script.task import Task
from moat.task import TASK,TASK_DIR, SCRIPT_DIR,SCRIPT
from moat.types.module import BaseModule
from moat.util import r_dict,r_show

import aio_etcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['ScriptCommand']

async def setup(self, meta=False):
	if meta:
		self.DIR=SCRIPT_DIR
	else:
		self.DIR=TASK_DIR
	await self.setup(None)
	etc = self.root.etcd
	return (await setup2(self,self.DIR))

async def setup2(self,d):
	tree = await self.root._get_tree()
	t = await tree.subdir(d)
	return t

class DefListCommand(Command):
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
		t = await setup(self, meta=True)
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
			async for task in tt.tagged(SCRIPT):
				path = task.path[len(SCRIPT_DIR):-1]
				if verbose:
					dump({path: r_dict(dict(task))}, stream=self.stdout)
				else:
					print('/'.join(path),task.get('summary',task.get('descr','??')), sep='\t',file=self.stdout)

class DefGetCommand(Command):
	name = "get"
	summary = "retrieve a script"
	description = """\
Scripts are stored in etcd at /meta/script/**/:code.

This command writes a single script to standard output.
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
			raise CommandError("You can't use --old and --new at the same time")
		if len(args) != 1:
			raise CommandError("Usage: … get path/to/script")

		t = await setup(self, meta=True)
		sc = t.lookup(args[0])
		sc = await sc.lookup(SCRIPT)
		sys.stdout.write(sc['old_code' if self.options.old else 'new_code' if self.options.new else 'code'])

class DefDeleteCommand(Command):
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
		td = await setup(self, meta=True)
		if not args:
			raise CommandError("You can't delete everything.")
		for k in args:
			t = await td.subdir(k,name=SCRIPT, create=False)
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

class DefTypeCommand(_ParamCommand):
	name = "type"
	_def = True
	DIR=SCRIPT_DIR
	TAG=SCRIPT
	NODE="types"
	summary = "Set script parameter types"
	description = """\
Display or change the data types for a script's parameters.
""" + _ParamCommand.description(True)

class DefParamCommand(_ParamCommand):
	_def = False
	DIR=SCRIPT_DIR
	TAG=SCRIPT
	NODE="values"
	summary = "Set default script parameters"
	description = """\
Display or change the default data for a script.
""" + _ParamCommand.description(False)

class ParamCommand(_ParamCommand):
	_def = False
	DIR=TASK_DIR
	TAG=TASK
	NODE="values"
	summary = "Set script parameters"
	description = """\
Display or change the data for a script instance.
""" + _ParamCommand.description(False)

class _DefAddUpdate:
	"""Mix-in to add or update a script"""

	async def do(self,args):
		try:
			data = {}
			if not self._update:
				data['language'] = 'python'

			name=""
			p=0

			path = args[p].rstrip('/').lstrip('/')
			if path == "":
				raise CommandError("Empty script path?")
			if path[0] == ':' or '/:' in path:
				raise CommandError("Don't add the tag")
			p+=1

			filepath = args[p]
			if filepath == "":
				raise CommandError("Empty script definition path?")
			if filepath == '.':
				if not self._update:
					raise CommandError("You need to provide a script")
				code = None
			elif filepath == '-':
				code = sys.stdin.read()
			else:
				with open(code,'r') as f:
					code = f.read()
			if len(code) < 5:
				raise CommandError("You need to provide a non-empty script")

			p+=1
			while p < len(args):
				try:
					k,v = args[p].split('=')
				except ValueError:
					break
				p += 1
				data[k] = v
			if not self._update and len(args) == p:
				raise CommandError("Scripts need a description")
			descr = " ".join(args[p:])
		except IndexError:
			raise CommandError("Missing parameters")

		t = await setup(self, meta=True)
		r = None
		try:
			script = await t.subdir(path,name=SCRIPT, create=False if self._update else None)
		except KeyError:
			raise CommandError("Script '%s' not found. (Use its path, not the name?)" % scriptpath)
		if self._update:
			if script['language'] != data['language']:
				raise CommandError("Wrong language (%s)" % (data['language'],))
		else:
			if 'language' in script:
				raise CommandError("Script '%s' already exists." % path)
			await script.set('language','python')

		if code is not None:
			compile(code, path, 'exec', dont_inherit=True)
			r = await script.set('new_code' if 'code' in script else 'code', code, sync=False)

		if descr:
			r = await script.set('descr', descr, sync=False)
		if data:
			for k,v in data.items():
				if v == "":
					try:
						r = await script.delete(k, sync=False)
					except KeyError:
						pass
				else:
					r = await script.set(k,v, sync=False, ext=True)
		await script.wait(mod=r)

class DefAddCommand(_DefAddUpdate,Command):
	name = "add"
	summary = "add a script"
	description = """\
Create a new script.

Arguments:

* the new script's path (must not exist)

* the file the script is stored in (must exist)
  Use '-' for standard input

* data=value parameters (script-specific, optional)

* a descriptive text (not optional)

"""
	_update = False

class DefUpdateCommand(_DefAddUpdate,Command):
	name = "change"
	summary = "change a script task"
	description = """\
Update a script.

Arguments:

* the script's path (required)

* the file the script is stored in (must exist)
  Use '-' for standard input
  Use '.' to not replace the script

* data=value parameters (script-specific, optional)

* a descriptive name (optional, to update)

"""
	_update = True


class DefCommand(SubCommand):
	subCommandClasses = [
		DefAddCommand,
		DefUpdateCommand,
		DefListCommand,
		DefGetCommand,
		DefDeleteCommand,
		DefTypeCommand,
		DefParamCommand,
	]
	name = "def"
	summary = "Define scripts"
	description = """\
Commands to set up and admin the scripts known to MoaT.
"""

class ListCommand(Command):
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
		t = await setup(self, meta=True)
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
				for task in script.get('tasks',{}).values():
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
	"""Mix-in to add or update a scripting task"""

	async def do(self,args):
		try:
			data = {}
			scriptdefpath=""
			name=""
			p=0

			if not self._update:
				scriptpath = args[p].rstrip('/').lstrip('/')
				if scriptpath == "":
					raise CommandError("Empty script path?")
				if scriptpath[0] == ':' or '/:' in scriptpath:
					raise CommandError("Don't add the tag")
				p+=1

			taskpath = args[p].rstrip('/').lstrip('/')
			if taskpath == "":
				raise CommandError("Empty task path?")
			if taskpath[0] == ':' or '/:' in taskpath:
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
		t = await setup(self, meta=False)
		if not self._update:
			try:
				td = await setup2(self, SCRIPT_DIR)
				scriptdef = await td.subdir(scriptpath,name=SCRIPT, create=False)
			except KeyError:
				raise CommandError("Taskdef '%s' not found" % scriptpath)

		try:
			script = await t.subdir(taskpath,name=SCRIPT, create=not self._update)
		except KeyError:
			raise CommandError("Task '%s' not found. (Use its path, not the name?)" % taskpath)
		if not self._update:
			await script.set('scriptdef', scriptpath, sync=False)
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
			
from .task import AddCommand as TaskAddCommand
class AddCommand(TaskAddCommand):
	name = "add"
	summary = "add a scripted task"
	description = """\
Create a new task for a script.

Arguments:

* the script's path (must exist)

* the new task's path (must not exist)

* data=value parameters (task-specific, optional)

* a descriptive text (not optional)

NB: Parameters affect the task, not the script. Use The "param" subcommand
    to set the script's "moat.data" variables.

"""

	async def do(self,args):
		t = await setup(self, True)
		try:
			s = await t.lookup(args[0],name=SCRIPT)
		except KeyError:
			raise CommandError("The script '%s' does not exist" % (args[0],))
		import pdb;pdb.set_trace()
		args = (args[1],"task/script","script="+args[0]) +tuple(args[2:])
		await super().do(args)
		sd = await s.subdir("tasks")
		k = await sd.set(None,args[1])
		t = await setup2(self, TASK_DIR)
		s = await t.lookup(args[1])
		await s.set("script_loc",k)

from .task import UpdateCommand as TaskUpdateCommand
class UpdateCommand(TaskUpdateCommand):
	name = "change"
	summary = "change a scripted task"
	description = """\
Update a scripted task.

Arguments:

* the task's path (must exist)

* data=value parameters (task-specific, optional)

* a descriptive name (optional, to update)

NB: Parameters affect the task, not the script. Use The "param" subcommand
    to modify the script's "moat.data" variables.

"""
	_update = True

	async def do(self,args):
		t = await setup(self, False)
		s = await t.lookup(args[0], name=TASK)
		sc = s['script']
		k = s['script_loc']
		args = (args[1],)+tuple(args[1:])
		await super().do(args)
		if s['script'] != sc:
			t = await setup2(self, SCRIPT_DIR)
			sd = await t.lookup(sc, name=SCRIPT)
			await sd['tasks'].delete(k)
			sd = await t.lookup(s['script'], name=SCRIPT)
			await sd['tasks'].set(k, '/'.join(s.path[len(TASK_DIR):-1]))


from moat.cmd.task import DeleteCommand as TaskDeleteCommand
class DeleteCommand(TaskDeleteCommand):
	def check(self,task):
		if task._get('taskdef').value != 'task/script':
			print("%s: not a script job, not deleted" % ('/'.join(self.path[len(TASK_DIR):-1]),), file=sys.stderr)
			return False
		return True

	async def do(self,args):
		t = await setup(self, False)
		s = await t.lookup(args[0], name=TASK)
		try:
			if s['taskdef'] != "task/script":
				raise CommandError("'%s' is not a scripting task!" % ('/'.join(self.path[len(TASK_DIR):-1]),))
			sc = s['script']
			k = s['script_loc']
		except KeyError:
			sc = None
		await super().do(args)
		if sc is not None:
			t = await setup2(self, SCRIPT_DIR)
			sd = await t.lookup(sc, name=SCRIPT)
			await sd['tasks'].delete(k)
		

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


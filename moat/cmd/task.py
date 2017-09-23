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

import asyncio
import os
import sys
import time
import types as py_types
from contextlib import suppress
from datetime import datetime
from yaml import dump
from collections.abc import Mapping

from qbroker.util import import_string
from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task
from moat.script.util import _ParamCommand
from moat.task import TASK,TASK_DIR, TASKDEF,TASKDEF_DIR, TASKSTATE,TASKSTATE_DIR, TASKSCAN_DIR, task_types, TASK_TYPE,TASK_DATA
from moat.task import TASKDEF_DEFAULT
from moat.types.module import BaseModule
from moat.types import TYPEDEF_DIR
from moat.util import r_dict,r_show

import aio_etcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['TaskCommand']

class Setup:
	DIR=TASK_DIR
	async def setup(self, meta=False):
		await super().setup()
		etc = self.root.etcd
		tree = await self.root._get_tree()
		t = await tree.subdir(self.DIR)
		return t

class DefSetup(Setup):
	DIR=TASKDEF_DIR

class DefInitCommand(DefSetup,Command):
	name = "init"
	summary = "Set up task definitions"
	description = """\
Task definitions are stored in etcd at /meta/task/**/:taskdef.

This command sets up that data. If you mention module or class names
on the command line, they are added, otherwise everything under
'moat.task.*' is used.

This also installs the root "task scanner" task, if no args are given.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="update existing values")

	def handleOptions(self):
		self.force = self.options.force

	async def do(self,args):
		tree = await self.root._get_tree()
		t = await self.setup(meta=True)
		if args:
			objs = []
			for a in args:
				m = import_string(a)
				if isinstance(m,py_types.ModuleType):
					from moat.script.util import objects
					n = 0
					for c in objects(m, Task, filter=lambda x:getattr(x,'taskdef',None) is not None):
						await t.add_taskdef(c, force=self.force)
						n += 1
					if self.root.verbose > (1 if n else 0):
						print("%s: %s command%s found." % (a,n if n else "no", "" if n==1 else "s"), file=self.stdout)
				else:
					if not isinstance(m,Task):
						raise CommandError("%s is not a task"%a)
					await t.add_taskdef(m, force=self.force)
		else:
			for c in task_types():
				await t.add_taskdef(c, force=self.force)

			from moat.script.main import DEFAULT_CONFIG
			mt = await tree.subdir(TYPEDEF_DIR)
			r = await tree.subdir(TASKDEF_DIR, name=TASKDEF_DEFAULT)
			rt = await r.subdir(TASK_TYPE)
			rv = await r.subdir(TASK_DATA)

			async def do_typ(rt,data):
				m = None
				for k,v in data.items():
					if isinstance(v,Mapping):
						m = await do_typ(await rt.subdir(k), v)
					else:
						t = type(v).__name__
						if t not in mt:
							raise RuntimeError("Don't know the type for %s" % (repr(v),))
						m = await rt.set(k,t)
				return m

			async def do_val(rt,data):
				m = None
				for k,v in data.items():
					if isinstance(v,Mapping):
						m = await do_val(await rv.subdir(k), v)
					else:
						m = await rv.set(k,v)
				return m

			m = await do_typ(rt,DEFAULT_CONFIG['run'])
			await rt.wait(m, tasks=True)
			m = await do_val(rv,DEFAULT_CONFIG['run'])

			r = await tree.subdir(TASKSCAN_DIR)
			from moat.task.collect import Collector
			await r.add_task(path=(),taskdef=Collector.taskdef, force=self.force)

		await t.wait()

class DefListCommand(DefSetup,Command):
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

class DefDeleteCommand(DefSetup,Command):
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

	async def do(self,args):
		td = await self.setup(meta=True)
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = td.tagged(TASKDEF)
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

class DefParamCommand(_ParamCommand,DefSetup,Command):
    _def = False
    DIR=TASKDEF_DIR
    TAG=TASKDEF
    NODE="data"
    summary = "Set default task parameters"
    description = """\
Display or change the default data for a task.
""" + _ParamCommand.description(False)

class ParamCommand(_ParamCommand,Setup,Command):
    _def = False
    DIR=TASK_DIR
    TAG=TASK
    NODE="data"
    summary = "Set task parameters"
    description = """\
Display or change the data for a task instance.
""" + _ParamCommand.description(False)


class DefCommand(SubCommand):
	subCommandClasses = [
		DefInitCommand,
		DefListCommand,
		DefParamCommand,
		DefDeleteCommand,
	]
	name = "def"
	summary = "Define tasks"
	description = """\
Commands to set up and admin the task definitions known to MoaT.
"""

class EnumCommand(Command):
	name = "enum"
	summary = "list jobs for etcd node"
	description = """\
		Show which job(s) should run for a given etcd node
		"""

	def addOptions(self):
		self.parser.add_option('-w','--watch',
			action="store_true", dest="watch",
			help="also monitor the node for changes")
	
	async def do(self,args):
		tree = await self.root._get_tree()

		if not len(args):
			args = ("",)
		else:
			if len(args) > 1 and self.options.watch:
				raise CommandError("You can only watch one node. Sorry.")
		for a in args:
			try:
				d = await tree.lookup(a)
			except KeyError:
				print("Node '%s' not found" % (a,), file=sys.stderr)
				continue
			try:
				coll = d.task_monitor
			except AttributeError:
				print("Node '%s' does not have tasks" % (d,), file=sys.stderr)
				continue
			def show(r):
				if len(r) > 1:
					r1 = r[1]
					if not isinstance(r1,str):
						r1 = '/'.join(r1)
				if r[0] == 'add':
					print("Task:"+r1, 'at', '/'.join(r[2]),*r[3:], file=self.stdout)
				elif r[0] == 'drop':
					print("Delete", r1, *r[2:], file=self.stdout)
				elif r[0] == 'scan':
					print("Subtask", r1, *r[2:], file=self.stdout)
				elif r[0] == 'watch':
					print('---', file=self.stdout)
					if not self.options.watch:
						raise StopIteration
				else:
					raise RuntimeError("Unknown response: "+repr(r))
			if hasattr(coll,'__aiter__'):
				async for r in coll:
					try:
						show(r)
					except StopIteration:
						break
			else:
				for r in coll:
					show(r)

class ListCommand(Setup,Command):
	name = "list"
	summary = "List tasks"
	description = """\
Tasks are stored in etcd at /task/**/:task.

This command shows that data. Depending on verbosity, output is
a one-line summary, human-readable detailed state, or details as YAML.
"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
			action="count", dest="this", default=0,
			help="Show the given job only (-tt for jobs one level below, etc.)")

	async def do(self,args):
		t = await self.setup(meta=False)
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
			async for task in tt.tagged(TASK, depth=self.options.this):
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
	"""Mix-in to add or update a task (too much)"""

	def addOptions(self):
		self.parser.add_option('-p','--parent',
			action="store", dest="parent",
			help="the node which this task depends on")

	async def do(self,args):
		try:
			data = {}
			taskdefpath=""
			name=""
			p=0

			taskpath = args[p].rstrip('/').lstrip('/')
			if taskpath == "":
				raise CommandError("Empty task path?")
			if taskpath[0] == ':' or '/:' in taskpath:
				raise CommandError("Don't add the tag")
			p+=1

			if not self._update:
				taskdefpath = args[p].rstrip('/').lstrip('/')
				if taskdefpath == "":
					raise CommandError("Empty task definition path?")
				if taskdefpath[0] == ':' or '/:' in taskdefpath:
					raise CommandError("Don't add the tag")
				p+=1
			while p < len(args):
				try:
					k,v = args[p].split('=')
				except ValueError:
					break
				p += 1
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
				taskdef = await td.subdir(taskdefpath,name=TASKDEF, create=False)
			except KeyError:
				raise CommandError("Taskdef '%s' not found" % taskdefpath)

		r = None
		try:
			task = await t.subdir(taskpath,name=TASK, create=not self._update)
		except KeyError:
			raise CommandError("Task '%s' not found. (Use its path, not the name?)" % taskpath)
		if not self._update:
			r = await task.set('taskdef', taskdefpath, sync=False)
		p = self.options.parent
		if p is not None:
			if p in ('','-'):
				with suppress(KeyError):
					r = await task.delete('parent', sync=False)
			else:
				r = await task.set('parent', p, sync=False)
		if descr:
			r = await task.set('descr', descr, sync=False)

		if data:
			for k,v in data.items():
				if v == "":
					try:
						r = await task.delete(k, sync=False)
					except KeyError:
						pass
				else:
					r = await task.set(k,v, sync=False, ext=True)
		await task.wait(mod=r)
			

class AddCommand(_AddUpdate,Setup,Command):
	name = "add"
	summary = "add a task"
	description = """\
Create a new task.

Arguments:

* the new task's path (must not exist)

* the task definition's path (must exist)

* data=value parameters (job-specific, optional)

* a descriptive text (not optional)

"""
	_update = False

class UpdateCommand(_AddUpdate,Setup,Command):
	name = "change"
	summary = "change a task"
	description = """\
Update a task.

Arguments:

* the task's path (required)

* data=value entries (deletes the key if value is empty)

* a descriptive text (optional, to update)

"""
	_update = True

class DeleteCommand(Setup,Command):
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

	def check(self, task):
		pass

	async def do(self,args):
		t = await self.setup(meta=False)
		res = 0
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = t
		for k in args:
			try:
				task = await t.subdir(k,name=TASK, create=False)
			except KeyError:
				raise CommandError("%s: does not exist"%k)
			if not self.check(task):
				res += 1
				continue
			if self.root.verbose:
				print("%s: deleted"%k, file=self.stdout)
			rec = None
			while True:
				p = task._parent
				if p is None: break
				p = p()
				if p is None: break
				if p is task: break
				try:
					await task.delete(recursive=rec)
				except etcd.EtcdDirNotEmpty:
					if rec:
						raise
					break
				rec = False
				task = p
		return res

class StateCommand(Command):
	name = "state"
	summary = "Show task status"
	description = """\
The status of running tasks is stored in etcd at /status/run/task/**/:task.

This command shows that information.
"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
			action="count", dest="this", default=0,
			help="Report on the given job only (-tt for jobs one level below, etc.)")
		self.parser.add_option('-r','--running',
			action="store_true", dest="running",
			help="Only list running jobs")
		self.parser.add_option('-e','--error',
			action="store_true", dest="error",
			help="Only list jobs with errors")
		self.parser.add_option('-c','--completed',
			action="store_true", dest="completed",
			help="Only list completed jobs")

	async def do(self,args):
		await self.root.setup()
		etc = self.root.etcd
		tree = await self.root._get_tree()
		t = await tree.subdir(TASKSTATE_DIR)

		if args:
			dirs = []
			for a in args:
				try:
					dirs.append(await t.subdir(a, create=False))
				except KeyError:
					print("'%s' does not exist" % (a,), file=sys.stderr)
		else:
			dirs = [t]

		sel_running = self.options.running
		sel_error = self.options.error
		sel_completed = self.options.completed
		if not (self.options.completed or self.options.running or self.options.error):
			sel_running = sel_error = sel_completed = True

		for tt in dirs:
			async for task in tt.tagged(TASKSTATE, depth=self.options.this):
				path = task.path[len(TASKSTATE_DIR):-1]
				date = task.get('debug_time','-')
				state = task.state
				if state == 'run':
					if 'started' in task:
						date = task['started']
					else:
						date = task['running']
				elif state == 'crash':
					date = task['started']
				else:
					date = task.get('stopped','?')
				if not isinstance(date,str):
					date = datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')

				if sel_running if state == 'run' else (sel_completed if state == 'ok' else sel_error):
					if self.root.verbose == 2:
						print('*','/'.join(path), sep='\t', file=self.stdout)
						for k,v in task.items():
							if isinstance(v,(float,int)) and 1000000000 < v < 10000000000:
								v = datetime.fromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S')
							elif isinstance(v,str):
								v = v.strip()
							else:
								v = str(v)
							print(k,('\n\t' if '\n' in v else '')+v.replace('\n','\n\t'), sep='\t',file=self.stdout)
					elif self.root.verbose > 1:
						dump({'/'.join(path):r_dict(dict(task))}, stream=self.stdout)
					else:
						print('/'.join(path),state,date,task.get('message','-'), sep='\t', file=self.stdout)

class TaskCommand(SubCommand):
	name = "task"
	summary = "Configure and define tasks"
	description = """\
Commands to set up and admin the task list known to MoaT.
"""

	subCommandClasses = [
		DefCommand,
		EnumCommand,
		AddCommand,
		UpdateCommand,
		ListCommand,
		DeleteCommand,
		StateCommand,
		ParamCommand,
	]
	fix = False


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

import asyncio
from etcd_tree import EtcFloat,EtcString, ReloadRecursive

from . import SCRIPT_DIR,SCRIPT, TASK_DIR,TASK
from moat.script.task import Task
from weakref import ref

import logging
logger = logging.getLogger(__name__)

class ScriptTimer(object):
	def __init__(self,parent,tm,fn):
		self.parent = ref(parent)
		self.fn = fn
		self.timer = asyncio.call_at(tm,self)
		self.parent._timers.add(self)
	def __call__(self):
		parent = self.parent()
		if parent is None:
			return
		self.parent._timers.delete(self)
		parent._q.put(fn)
	def __del__(self):
		self.timer.cancel()

class MoatScript(object):
	"""\
		The class which controls interactions of a user script with the
		rest of MoaT.
		"""
	_setup_called = False
	_starting = None # Future

	def __init__(self, task, reg):
		self._reg = reg
		self._task = task
		self.loop = reg.loop
		self._q = asyncio.Queue(loop=self.loop)
		self._start_proc = []
		self._stop_proc = []
		self._run_proc = None
		self._timers = set()
		self._job = asyncio.ensure_future(self._run)
		self.stopping = asyncio.Future(loop=self.loop)
		self.stopping.add_done_callback(self._run_end)
	
	def self._run_end(self, f=None):
		self.q.put_nowait(None)
	
	async def _run(self):
		try:
			while True:
				f = await self.q.get()
				if f is None:
					return
				await f()

		except Exception as exc:
			if self.stopping.done:
				await self._task.set_error("script",exc)
			else:
				self.stopping.set_exception(exc)
		else:
			if not self.stopping.done:
				self.stopping.set_result(None)

	async def _main(self):
		if self._run_proc is None:
			await self.stopping
		else:
			await self._run_proc()

	async def _start(self):
		while self._start_proc:
			fn = self._start_proc.pop(0)
			await fn()

	async def _stop(self):
		while self._start_proc:
			fn = self._start_proc.pop()
			try:
				await fn()
			except Exception as exc:
				logger.exception("%s: %s" % (self,fn))
		
	def _did_setup(self):
		if not self._setup_called:
			raise RuntimeError("You didn't call moat.setup()!")

	@property
	def root(self):
		return self.reg.root

	def setup(self, async=False):
		if self._setup_called:
			raise RuntimeError("Don't call moat.setup() twice!")
		self.async = async
		self._setup_called = True
	
	def _on_proc(self, what, fn=None):
		self._did_setup()
		def at_start(fn):
			what(fn)
			return fn
		if fn is not None:
			return _start(fn)
		else:
			return at_start

	def on_start(self,fn=None):
		return self._on_proc(self._start_proc.append,fn)
	def on_stop(self,fn=None):
		return self._on_proc(self._stop_proc.append,fn)

	def _set_run(self,fn):
		if self._run_proc is not None:
			raise RuntimeError("Don't call moat.run() twice!")
		self._run_proc = fn
	def run(self,fn=None):
		return self._on_proc(self,_set_run,fn)

    def wait(self, *tm, current=None, now=None):
		if now is None:
			now = time()
		t = self.time_at(*tm,current=current,now=now) - now
		if t < 0.1:
			t = 0.1
		return asyncio.sleep(t, loop=self.loop)

	def run_at(self, *tm, current=None, now=None, fn=None):
		t = self.time_at(*tm,current=current,now=now)
		def _trigger(fn):
			self.timers.add(ScriptTimer(self,t,fn))
		if fn is None:
			return _trigger
		else:
			return _trigger(fn)

	def time_at(self, *tm, current=None, now=None):
		"""\
			Return the next timestamp after @now (defaults to the current
			time) at which the timespec in @tm applies (@current=True), no
			longer applies (@current=False) or applies again
			(@current=None, the default).
			"""
		from moat.times import time_until
		if now is None:
			now = time()
		if current is not True:
			now = time_until(tm,now=now,invert=True)
		if current is not False
			now = time_until(tm,now=now,invert=False)
		return now

	def end(self):
		self.stopping.set_result(None)

class Scriptor(Task):
	"""\
		This task runs a script.

		Scripts are stored in etcd at /meta/script/…/:code/code.
		The '…' part is stored in the task's "script" attribute.
		""" % ('/'.join(TASKSCAN_DIR),)

	taskdef="task/script"
	summary="A Task which runs a user-defined script"
	schema = {}

	async def task(self):
		root = await self.cmd.root._get_tree()
		script = self['script']

		try:
			reg = Reg(self)
			moat = MoatScript(self,reg)

			env = {'moat':moat}
			eval(self.taskdir.code,env)

			await moat._start()
			await moat._main()

		finally:
			await moat._stop()
			await reg.free()

		

# -*- Mode: Python; test-case-name: test_command -*-
# vi:si:et:sw=4:sts=4:ts=4
# on 2015-11-14
##BP

"""
Class for managing tasks.
"""

import asyncio
from etcd_tree.etcd import EtcTypes
from etcd_tree.node import EtcFloat,EtcBase
import etcd
import inspect
from time import time
from traceback import format_exception
import weakref
from bdb import BdbQuit

from moat.task import _VARS, TASK_DIR,TASKDEF_DIR,TASK,TASKDEF, TASKSTATE_DIR,TASKSTATE
from moat.util import do_async

import logging
logger = logging.getLogger(__name__)

import os
min_timeout = float(os.environ.get('MOAT_DEBUG_TIMEOUT',0))

class _NOTGIVEN:
	pass

class JobIsRunningError(RuntimeError):
	"""The job is already active"""
	pass

class JobMarkGoneError(RuntimeError):
	"""The job's 'running' mark in etcd is gone (timeout, external kill)"""
	pass

class JobParentGoneError(RuntimeError):
	"""The job entry's 'parent' points to something that does not exist."""
	pass

@asyncio.coroutine
def coro_wrapper(proc):
	"""\
		This code is responsible for turning whatever callable you pass in
		into a "yield from"-style coroutine.
		"""
	did_call = False
	if inspect.iscoroutinefunction(proc):
		proc = proc()
		did_call = True
	if inspect.isawaitable(proc):
		return (yield from proc.__await__())
	if inspect.iscoroutine(proc):
		return (yield from proc)
	if not did_call and callable(proc):
		proc = proc()
	return proc

class Task(asyncio.Task):
	"""\
		I am the base class for a task to be executed within MoaT.

		`self.loop` contains the asyncio loop to use.
		Set `_global_loop` to True if you need to fork a process. (TODO)

		The `ttl` and `refresh` config values control how long the running
		state in etcd lasts before it is cleaned up; `refresh` says how
		often it is renewed within that timeframe.
		"""
	taskdef = None
	summary = """This is a prototype. Do not use."""
	schema = {}
	doc = None

	_global_loop=False

	def __init__(self, cmd, name, taskdir=None, parents=(), config={}, _ttl=None,_refresh=None, **cfg):
		"""\
			This is MoaT's standard task runner.
			It takes care of noting the task's state in etcd.
			The task will be killed if there's a conflict.

			@cmd: the command object from `moat run`.
			@name: the etcd tree to use (without /task and :task prefix/suffix)
			@config: some configuration data or this task, possibly an etcd_tree object

			@_ttl: time-to-live for the process lock.
			@_refresh: how often the lock is refreshed within the TTL.
			Thus, ttl=10 and refresh=4 would refresh the lock every 2.5
			seconds. The minimum is 1. A safety margin of 0.1 is added
			internally.

			If _ttl is a callable, it must return a (ttl,refresh) tuple.
			_refresh is ignored in that case.

			@parents contains a list of etcd node paths which must exist for the task to run.
			"""
		self.loop = cmd.root.loop
		super().__init__(coro_wrapper(self.run), loop=self.loop)
		if isinstance(name,(list,tuple)):
			assert len(name)
			path = name
			name = '/'.join(name)
		else:
			path = tuple(name.split('/'))
		assert name[0] != '/'
		assert name[-1] != '/'
		assert '//' not in name

		self.cmd = cmd
		self.config = config
		self.cfg = cfg
		self._ttl = config.get('ttl',None) if _ttl is None else _ttl
		self._refresh = config.get('refresh',None) if _refresh is None else _refresh
		self.name = name
		self.path = path
		self.parents = parents
		self.taskdir = taskdir

	@classmethod
	def task_info(cls,tree):
		"""\
			Retrieve the data about this task that should be stored in etcd.
			Returns (classname,dict).

			To override: call super(), then add to dict.
			"""
		dir = dict(
			language='python',
			code=cls.__module__+'.'+cls.__name__,
			summary=cls.summary,
			)
		if cls.schema is not None:
			d['data'] = cls.schema
		return cls.name, dir

	async def run(self):
		"""Main code for task control. Don't override."""
		r = self.cmd.root
		await r.setup(self)
		run_state = await _run_state(r.tree,self.path)
		main_task = None
		self.tree = await r._get_tree()

		## Install checks for the requisite nodes to be present.
		gone = None
		prm = []
		def parent_check(x):
			nonlocal gone
			if x._seq: return
			try:
				logger.info('CANCEL Q %s %s',self.path,x.path)
				main_task.cancel()
			except Exception: pass
			gone = x.path

		for pr in self.parents:
			try:
				parent = await r.tree.lookup(*pr)
				prm.append(parent.add_monitor(parent_check))
			except (KeyError,etcd.EtcdKeyNotFound) as ex:
				await run_state.set("message", "Missing: "+'/'.join(pr))
				raise JobParentGoneError(self.name, pr) from ex

		## TTL calculation
		def get_ttl():
			if callable(self._ttl):
				ttl,refresh = self._ttl()
			else:
				ttl = self._ttl if self._ttl is not None else int(r.cfg['config']['run']['ttl'])
				refresh = self._refresh if self._refresh is not None else float(r.cfg['config']['run']['refresh'])
				if refresh < 1:
					refresh = 1
			assert refresh>=1, refresh
			ttl = max(ttl,min_timeout)
			refresh = (ttl/(refresh+0.1))
			return ttl,refresh
		ttl,refresh = get_ttl()

		## set 'running'
		logger.debug("Starting %s: %s",self.name, self.__class__.__name__)
		try:
			if 'running' in run_state:
				raise etcd.EtcdAlreadyExist(message=self.name, payload=run_state['running']) # pragma: no cover ## timing dependant
			ttl = int(ttl)
			if ttl < 1:
				raise ValueError("TTL must be at least 1",ttl)
			cseq = await run_state.set("running",time(),ttl=ttl)
		except etcd.EtcdAlreadyExist as exc:
			logger.warn("Job is already running: %s",self.name)
			raise JobIsRunningError(self.name) from exc
		mod = await run_state.set("started",time())
		await run_state.wait(mod)
		keep_running = False # if it's been superseded, do not delete

		if isinstance(self.config,EtcBase):
			_note = self.config.add_monitor(lambda _: self.cfg_changed())

		def aborter():
			"""If the updater doesn't work (e.g. if etcd isn't reachable)
			this will terminate the task."""
			logger.error("Aborted %s", self.name)
			nonlocal killer
			try:
				logger.info('CANCEL 5 %s',main_task)
				main_task.cancel()
			except Exception: pass
			try:
				logger.info('CANCEL 6 %s',run_task)
				run_task.cancel()
			except Exception: pass
			killer = None
		killer = r.loop.call_later(max(ttl,min_timeout), aborter)

		async def updater(refresh):
			# Periodically refresh the "running" entry.

			# The initial sleep is paired with the initial TTL; otherwise, if
			# somebody changed the TTL from 1 to 100 just as we're starting up,
			# the refresh value would be far too long, the old 
			nonlocal killer
			await asyncio.sleep(refresh, loop=r.loop)
			while True:
				ttl,refresh = get_ttl()
				logger.debug("Run marker check %s",self.name)
				if 'running' not in run_state or run_state._get('running')._cseq != cseq:
					logger.warn("Run marker deleted %s",self.name)
					raise JobMarkGoneError(self.name)
				try:
					await run_state.set("running",time(),ttl=ttl)
				except (etcd.EtcdKeyNotFound,etcd.EtcdCompareFailed) as exc:
					raise JobMarkGoneError(self.name) from exc
				if killer is None:
					break
				logger.info('CANCEL 7 %s',killer)
				killer.cancel()
				def mtc():
					logger.info('CANCEL 8 %s',killer)
					main_task.cancel()
				killer = r.loop.call_later(max(ttl,min_timeout),mtc)
				logger.debug("Run marker refreshed %s",self.name)
				await asyncio.sleep(refresh, loop=r.loop)
				
		# Now start the updater and the main task.
		run_task = asyncio.ensure_future(updater(refresh), loop=r.loop)
		main_task = asyncio.ensure_future(self.task(), loop=r.loop)
		res = None
		try:
			try:
				try:
					d,p = await asyncio.wait((main_task,run_task), loop=r.loop, return_when=asyncio.FIRST_COMPLETED)
				finally:
					if killer is not None:
						logger.info('CANCEL 9 %s',killer)
						killer.cancel()
				logger.debug("Ended %s :: %s :: %s",self.name, repr(d),repr(p))
			except asyncio.CancelledError:
				# Cancelling an asyncio.wait() doesn't propagate
				logger.debug("Cancelling %s",self.name)
				try:
					logger.info('CANCEL 10 %s',main_task)
					main_task.cancel()
					await main_task
				except Exception:
					pass
			# At this point at least one of the two jobs has definitely exited
			# and the "killer" timer is either cancelled or has triggered.
			if run_task.done():
				# The TTL could not be refreshed: kill the job.
				if not run_task.cancelled() and isinstance(run_task.exception(), JobMarkGoneError):
					keep_running = True
				if not main_task.done():
					logger.info('CANCEL 11 %s',main_task)
					main_task.cancel()
					try: await main_task
					except Exception: pass
					# We'll get the error later.
			else:
				assert main_task.done()
				try:
					logger.info('CANCEL 12 %s',run_task)
					run_task.cancel()
				except Exception: pass
				try: await run_task
				except Exception: pass
				# At this point we don't care why the run_task thread died.

			assert main_task.done()
			assert run_task.done()

			if main_task.cancelled():
				# Killed because of a timeout / refresh problem. Major fail.
				await run_state.set("state","fail")
				if gone is not None:
					await run_state.set("message", "Missing: "+'/'.join(gone))
				elif killer is None:
					await run_state.set("message", "Aborted by timeout")
				else:
					await run_state.set("message", str(run_task.exception()))
				run_task.result()
				assert False,"the previous line should have raised an error" # pragma: no cover
			else:
				# Not killed, so it either returned a result …
				try:
					res = main_task.result()
				except Exception as exc:
					# … or not.
					exc.__context__ = None # the cancelled run_task is not interesting
					await run_state.set("state","error")
					await run_state.set("message",str(exc))
					await run_state.set("debug","".join(format_exception(exc.__class__,exc,exc.__traceback__)))
					await run_state.set("debug_time",str(time()))
					raise
				else:
					await run_state.set("state","ok")
					await run_state.set("message",str(res))
					return res
		finally:

			# Now clean up everything
			await run_state.set("stopped",time())
			if not keep_running and 'running' in run_state:
				try:
					await run_state.delete("running")
				except Exception as exc:
					logger.exception("Could not delete 'running' entry")
			await run_state.wait()

			logger.debug("Ended %s: %s",self.name, res)

	def cfg_changed(self):
		"""\
			Override this to notify your task about changed configuration values.
			"""
		pass

	async def task(self):
		"""\
			Override this to actually do the task's job.
			"""
		raise NotImplementedError("You need to write the code that does the work!")

async def _run_state(tree,path):
	"""\
		Get a tree for the job's state.

		Tests use this to manipulate the state behind the testee's back.
		"""
	run_state = await tree.subdir(TASKSTATE_DIR+path+(TASKSTATE,))
	return run_state


class TaskMaster(asyncio.Future):
	"""\
		An object which controls running and restarting a task,
		as specified in etcd.
		"""
	current_retry = 1
	path = None
	job = None
	timer = None
	exc = None

	def __init__(self, cmd, path, callback=None, **cfg):
		"""\
			Set up the non-async part of our task.
			@cmd: the command this is running because of.
			@path: the job's path under /task
			@callback(status,value): called with ("started",None), ("ok",result) or ("error",exc)
			 whenever the job state changes

			You need to call "await tm.init()" before using this.
			"""
		self.loop = cmd.root.loop
		self.tree = cmd.root.tree
		self.cmd = cmd
		assert isinstance(path,tuple)
		self.path = path
		self.name = '/'.join(path) # for now
		self.cfg = cfg
		self.vars = {}
		self.callback = callback

		super().__init__(loop=self.loop)
		
	async def init(self):
		"""Async part of initialization"""
		self.task = await self.tree.subdir(TASK_DIR+self.path+(TASK,))
		await self.task.taskdef_ready.wait()
		self.taskdef_name = self.task.taskdef_name
		if self.task.taskdef is None:
			raise RuntimeError("incomplete task: "+'/'.join(self.task.path))

		self.gcfg = self.cmd.root.etc_cfg['run']
		self.rcfg = self.cmd.root.cfg['config']['run']
		self._m1 = self.task.add_monitor(self.setup_vars)
		self._m2 = self.task.taskdef.add_monitor(self.setup_vars)
		self._m3 = self.gcfg.add_monitor(self.setup_vars)

		self.setup_vars()
		
		self._start()
	
	def trigger(self):
		"""Calls the task's trigger() function, causing immediate processing.
			Used for testing."""
		self.job.trigger()

	def task_var(self,k):
		for cfg in (self.cfg, self.task, self.task.taskdef, self.gcfg, self.rcfg):
			if k in cfg:
				return cfg[k]
		raise KeyError(k)

	def setup_vars(self, _=None):
		"""Copy task variables from etcd to local vars"""
		# First, check the basics
#		changed = set()
		if self.taskdef_name != self.task.taskdef_name:
			# bail out
			raise RuntimeError("Command changed/deleted: %s / %s" % (self.taskdef_name,self.task.get('taskdef','')))
		self.name = self.task.get('name','/'.join(self.path))
		for k in _VARS:
			v = self.task_var(k)
#			if self.vars[k] != v:
#				changed.add(k)
			self.vars[k] = v
#		if changed:
		self.vars.update(self.cfg)

	def _get_ttl(self):
		return self.vars['ttl'], self.vars['refresh']

	def _start(self):
		p=[self.task.path]
		if 'parent' in self.task:
			p.append(self.task['parent'].value.split('/'))
		self.job = self.task.cls(self.cmd, self.name, parents=p, taskdir=self.task, config=self.task._get('data',{}), _ttl=self._get_ttl, **self.cfg)
		self.job.add_done_callback(self._job_done)
		if self.callback is not None:
			self.callback("start")

	async def cancel_job(self):
		logger.info('CANCEL 13 %s',self)
		try:
			self.cancel()
		except Exception:
			return
		if self.job is not None:
			try: 
				logger.info('CANCEL 14 %s',self.job)
				self.job.cancel()
				await self.job
			except Exception:
				pass
		if self.timer is not None:
			try:
				logger.info('CANCEL 15 %s',self.timer)
				self.timer.cancel()
			except Exception:
				pass

	def _timer_done(self):
		assert self.job is None
		assert self.timer is not None
		self.timer = None
		self._start()

	def _job_done(self, f):
		assert f is self.job # job ended
		assert self.timer is None
		try:
			res = self.job.result()
		except asyncio.CancelledError as exc:
			if not self.done():
				self.set_exception(exc)
			return
		except Exception as exc:
			# TODO: limit the number of retries,
			# this code only does 0 (retry=0) or 1 (max-retry=0) or inf (neither).
			if self.callback is not None:
				try:
					self.callback("error",exc)
				except Exception as e:
					logger.exception("during callback %s",self.callback)
			if self.exc is None:
				self.current_retry = self.vars['retry']
			else:
				self.current_retry = min(self.current_retry + self.vars['retry']/2, self.vars['max-retry'])
			self.exc = exc
			if not self.current_retry or isinstance(exc,(AttributeError,BdbQuit)):
				self.set_exception(exc)
				return
		else:
			if self.callback is not None:
				if res is None:
					pres = ()
				else:
					pres = (res,)
				self.callback("ok",*pres)
			self.exc = None
			self.current_retry = self.vars['restart']
			if not self.current_retry:
				self.set_result(res)
				return
		finally:
			self.job = None

		self.timer = self.loop.call_later(self.current_retry,self._timer_done)



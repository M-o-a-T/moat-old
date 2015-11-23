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

from . import Command
import asyncio
from time import time

class StdCommand(Command):
	
	_run_state = None
	async def run_state(self):
		if self._run_state is None:
			from etctree.node import mtFloat
			from etctree.etcd import EtcTypes
			types = EtcTypes()
			types.register('started', cls=mtFloat)
			types.register('stopped', cls=mtFloat)
			types.register('running', cls=mtFloat)
			self._run_state = await self.root.etcd.tree("/status/run/%s/%s"%(self.root.app,self.fullname), immediate=True, types=types)
		return self._run_state

	async def run(self, cmd, *a, _ttl=None,_refresh=None, **k):
		"""\
			This is MoaT's standard task runner.
			It takes care of noting the task's state in etcd and will kill
			the task if there's a conflict.
			"""
		r = self.root
		await r.setup()
		ttl = _ttl if _ttl is not None else int(self.root.cfg['config']['run']['ttl'])
		refresh = _refresh if _refresh is not None else float(self.root.cfg['config']['run']['refresh'])
		run_state = await self.run_state()

		if 'running' in run_state:
			raise RuntimeError("Run marker already exists")
		cseq = await run_state.set("running",time(),ttl=ttl)
		await run_state.set("started",time())
		await run_state._wait()

		async def updater():
			while True:
				if 'running' not in run_state or run_state._get('running')._cseq != cseq:
					raise RuntimeError("Run marker has been deleted")
				await run_state.set("running",time(),ttl=ttl)
				await asyncio.sleep(ttl/(refresh+0.1), loop=r.loop)
				
		run_task = asyncio.ensure_future(updater(), loop=r.loop)
		main_task = asyncio.ensure_future(cmd(*a,**k), loop=r.loop)
		d,p = await asyncio.wait((main_task,run_task), loop=r.loop, return_when=asyncio.FIRST_COMPLETED)
		if run_task.done():
			if not main_task.done():
				main_task.cancel()
				try: await main_task
				except Exception: pass
		else:
			assert main_task.done()
			run_task.cancel()
			try: await run_task
			except Exception: pass

		if main_task.cancelled():
			await run_state.set("state","fail")
			await run_state.set("message",str(run_task.exception()))
			run_task.result()
			assert False,"the previous line should have raised an error"
		else:
			try:
				res = main_task.result()
				await run_state.set("state","ok")
				await run_state.set("message",str(res))
			except Exception as exc:
				await run_state.set("state","error")
				await run_state.set("message",str(exc))
				try: await run_state.delete("running")
				except Exception: pass
				await run_state._wait()
				raise
		await run_state.set("stopped",time())
		try: await run_state.delete("running")
		except Exception: pass
		await run_state._wait()


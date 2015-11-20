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

class StdCommand(Command):
	async def run(self, cmd):
		r = self.root
		ttl = float(self.root.cfg['config']['run']['ttl'])
		refresh = float(self.root.cfg['config']['run']['refresh'])
		run_state = await r.etcd.tree("/status/run/%s/%s", r.app,self.fullname, immediate=True)

		async def updater():
			await run_state.set("started",time())
			try:
				while True:
					await run_state.set("running",time(),ttl=ttl)
					await run_state._wait()
					await asyncio.sleep(ttl/refresh, loop=r.loop)
			finally:
				await run_state.delete("running")
				await run_state._wait()
				

		run_task = asyncio.async(self._updater(), loop=r.loop)
		main_task = asyncio.async(cmd, loop=r.loop)
		await asyncio.wait((main_task,run_task), loop=r.loop, return_when=asyncio.FIRST_COMPLETED)
		if run_task.done():
			if not main_task.done():
				main_task.cancel()
		else:
			assert main_task.done()
			run_task.cancel()
		if main_task.cancelled():
			await run_state.set("state","fail")
			await run_state.set("message",str(run_task.exception()))
		else:
			try:
				res = main_task.result()
				await run_state.set("state","ok")
				await run_state.set("message",str(res))
			except Exception as exc:
				await run_state.set("state","error")
				await run_state.set("message",str(exc))
				raise
		await run_state.set("stopped",time())


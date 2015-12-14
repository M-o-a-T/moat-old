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

import asyncio

from ..script.task import Task
from etcd_tree.node import mtFloat

class Sleeper(Task):
	"""This task just waits for a configured amount of time before exiting.
		You can use it in a 'moat run -K' command to limit runtimes."""
	name="test/sleep"
	summary="A simple delay"

	@classmethod
	def types(cls,tree):
		super().types(tree)
		tree.register(cls=mtFloat)
		
	async def task(self):
		await asyncio.sleep(self.cfg.value, loop=self.loop)
	
class Error(Task):
	name="test/error"
	description="""This task always errors out."""
	summary="A simple RuntimeError"

	async def task(self):
		raise RuntimeError("I don't wanna dance")

class SleepError(Sleeper):
	name="test/sleep/error"
	description="""This task waits for a configured amount of time before raising an error."""
	summary="""A delay, terminated by an error"""

	async def task(self):
		await asyncio.sleep(self.cfg.value, loop=self.loop)
		raise RuntimeError("Don't wanna dance no mo-ooore")

	

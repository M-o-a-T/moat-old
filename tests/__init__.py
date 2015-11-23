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
import pytest
import subprocess
from functools import wraps
from socket import socket
import time
import gc

import logging
logging.basicConfig(filename='test.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.captureWarnings(True)

import warnings
warnings.filterwarnings("ignore")

async def is_open(port):
	s = socket()
	n = 0
	while n < 30:
		try:
			s.connect(("127.0.0.1", port))
		except Exception:
			n += 1
			time.sleep(0.1)
		else:
			s.close()
			break
	else: # pragma: no cover
		s.close()
		raise RuntimeError("Port did not open")

class ProcessHelper(asyncio.SubprocessProtocol):
	def __init__(self, proc, *args, loop=None, **kw):
		self.proc = proc
		self.args = args
		self.kw = kw
		self.fd = [b'',b'',b'']
		if loop is None:
			loop = asyncio.get_event_loop()
		else:
			asyncio.set_event_loop(loop)
			# required for waiting on a process
		self._loop = loop

	def pipe_data_received(self,fd,data):
		self.fd[fd] += data
	
	def process_exited(self):
		if not self.done.done():
			self.done.set_result(self.get_returncode())

	def connection_lost(self,exc):
		if self.done.done():
			return
		else: # pragma: no cover
			if exc is None:
				self.done.set_result(True)
			else:
				self.done.set_exception(exc)

	async def start(self):
		self.done = asyncio.Future(loop=self._loop)
		self.transport,_ = await self._loop.subprocess_exec(lambda: self, self.proc,*(str(x) for x in self.args), **self.kw)
		logger.debug("Started: %s",self.proc)

	def stop(self):
		self.transport.terminate()
		return self.wait()
	stop._is_coroutine = True

	def kill(self):
		self.transport.kill()
		return self.wait()
	kill._is_coroutine = True

	async def wait(self):
		await self.done
		return self.done.result()


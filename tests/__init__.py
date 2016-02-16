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
from moat.script.main import Moat
import io
import os
from yaml import safe_load

import logging
logger = logging.getLogger(__name__)

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
		assert loop is not None
		asyncio.set_event_loop(loop)
		# required for waiting on a process
		self._loop = loop

	def pipe_data_received(self,fd,data):
		self.fd[fd] += data
	
	def connection_lost(self,exc):
		if self.done.done():
			return # pragma: no cover
		else:
			if exc is None:
				self.done.set_result(self._transport.get_returncode())
			else:
				self.done.set_exception(exc) # pragma: no cover

	async def start(self):
		self.done = asyncio.Future(loop=self._loop)
		self._transport,_ = await self._loop.subprocess_exec(lambda: self, self.proc,*(str(x) for x in self.args), **self.kw)
		logger.debug("Started: %s",self.proc)

	def stop(self):
		self._transport.terminate()
		return self.wait()
	stop._is_coroutine = True

	def kill(self):
		self._transport.kill()
		return self.wait()
	kill._is_coroutine = True

	async def wait(self):
		await self.done
		return self.done.result()

class StoreHandler(logging.Handler):
	def __init__(self,cmd):
		super().__init__()
		self.cmd = cmd
	def emit(self, record):
		self.cmd.debug_log.append(record)

class MoatTest(Moat):
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._stdout = io.StringIO()
		self._width = 9999

	def parse_hook(self):
		self.debug_log = []
		h = StoreHandler(self)
		logging.getLogger().addHandler(h)

	async def parse(self,cmd):
		if isinstance(cmd,str):
			cmd = cmd.split(' ')
		return (await super().parse(cmd))

	@property
	def stdout_data(self):
		return self._stdout.getvalue()
	def in_stdout(self,s):
		return s in self.stdout_data
	def assert_stdout(self,s):
		assert s == self.stdout_data

def load_cfg(cfg):
	global cfgpath
	if os.path.exists(cfg):
		pass
	elif os.path.exists(os.path.join("tests",cfg)): # pragma: no cover
		cfg = os.path.join("tests",cfg)
	elif os.path.exists(os.path.join(os.pardir,cfg)): # pragma: no cover
		cfg = os.path.join(os.pardir,cfg)
	else: # pragma: no cover
		raise RuntimeError("Config file '%s' not found" % (cfg,))

	cfgpath = cfg
	with open(cfg) as f:
		cfg = safe_load(f)

	from logging.config import dictConfig
	cfg['config']['logging']['disable_existing_loggers'] = False
	dictConfig(cfg['config']['logging'])
	logging.captureWarnings(True)
	logger.debug("Test %s","starting up")
	return cfg


cfg = load_cfg(os.environ.get('MOAT_TEST_CFG',"test.cfg"))


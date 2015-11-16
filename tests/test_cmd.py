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
from time import time
import io
from moat.script.main import Moat

from . import ProcessHelper

class MoatTest(Moat):
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._stdout = io.StringIO()
		self._width = 9999

	def parse(self,cmd):
		if isinstance(cmd,str):
			cmd = cmd.split(' ')
		return super().parse(cmd)

	def in_stdout(self,s):
		return s in self._stdout.getvalue()
	def in_stderr(self,s):
		return s in self._stderr.getvalue()

def test_cmd(event_loop):
	m = MoatTest()
	m.parse("test")



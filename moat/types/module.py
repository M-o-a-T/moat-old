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

"""\
Module Interface

This code implements basic modularization.

Actually loading the code is performed in moat.types.etcd
"""

import logging
logger = logging.getLogger(__name__)

class BaseModule(object):
	"""\
		This is the parent class for MoaT modules.

		A Module is a subsystem that extends MoaT with new devices and
		buses.

		"""

	prefix = None
	summary = "Base class for modules"
	doc = None # use the docstr if empty
	
	@classmethod
	def entries(cls):
		"""Enumerate subsys,codepath pairs"""
		if False: yield None

	@classmethod
	def task_types(cls,root):
		"""Enumerate taskdef classes"""
		if False: yield None
		#from moat.task import task_types as ty
		#return ty('moat.ext.onewire.task')

def modules(base="moat.ext"):
	from moat.script.util import objects

	# This filter ignores derived classes which do not set a prefix
	return objects(base, BaseModule, filter=lambda x:x.__dict__.get('prefix',None) is not None)


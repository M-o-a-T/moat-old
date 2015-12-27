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

"""List of known Tasks"""

import os
from ..script.util import objects

import logging
logger = logging.getLogger(__name__)

TASK_DIR = '/task'
TASKDEF_DIR = '/meta/task'
TASK = ':task'
TASKDEF = ':taskdef'
TASKSTATE_DIR = '/status/run'
TASKSTATE = ':task'

_VARS = {'ttl','refresh','restart','retry','max-retry'}

def tasks():
	from ..script.task import Task
	return objects(__name__, Task)

def task_var_types(types):
	from etcd_tree.etcd import EtcTypes
	from etcd_tree.node import EtcFloat,EtcInteger
	for t in _VARS:
		if t == "ttl":
			types.register(t)(EtcInteger)
		else:
			types.register(t)(EtcFloat)
	
def task_state_types(types):
	from etcd_tree.etcd import EtcTypes
	from etcd_tree.node import EtcFloat
	types.register('started')(EtcFloat)
	types.register('stopped')(EtcFloat)
	types.register('running')(EtcFloat)
	types.register('debug_time')(EtcFloat)
	

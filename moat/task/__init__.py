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

"""List of known Tasks"""

import os
from etcd_tree import EtcDir,EtcFloat

import logging
logger = logging.getLogger(__name__)

# Possible tasks: what shall run where
# written by "moat task add …"
TASK_DIR = ('task',)
TASK = ':task'
TASKSCAN_DIR = TASK_DIR+('moat','scan')

# Task descriptions: what kind of tasks exist?
# written by "moat task def init"
TASKDEF_DIR = ('meta','task')
TASKDEF = ':taskdef'
TASKDEF_DEFAULT = ':default'

# task-specific types and (default) values
TASK_REF = 'taskdef' # taskdef link
TASK_TYPE = 'types' # task-specific data types and (default) values
TASK_DATA = 'data' # … and their default values

# Scripts: dynamic code
# written by "moat script def add"
SCRIPT_DIR = ('meta','script')
SCRIPT = ':code'

# script-specific types and (default) values; as in TASK_
SCRIPT_REF = 'script'
SCRIPT_TYPE = 'script_types'
SCRIPT_DATA = 'script_data'

# Task state: which tasks are currently running?
# written by "moat task run", obviously
TASKSTATE_DIR = ('status','run')
TASKSTATE = ':task'

def task_types(prefix=__name__):
	"""Enumerate the task types known to Moat's code."""
	from ..script.task import Task
	from ..script.util import objects
	return objects(prefix, Task, filter=lambda x:x.__dict__.get('taskdef',None) is not None)

class TaskDir(EtcDir):
	pass


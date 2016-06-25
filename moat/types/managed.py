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
from etcd_tree import EtcString,EtcDir,EtcFloat,EtcInteger,EtcValue, ReloadRecursive
import aio_etcd as etcd
from time import time
from weakref import ref

from moat.util import do_async
from moat.types import TYPEDEF_DIR,TYPEDEF, type_names
from moat.dev import devices, DEV
from dabroker.unit.rpc import CC_DATA

import logging
logger = logging.getLogger(__name__)

__all__ = ('ManagedEtcDir',)

class ManagedEtcThing(object):
	"""\
		A mix-in for something that may or may not be managed, but its subdirs might be.
		"""
	@property
	def manager(self):
		p = self.parent
		if p is not None:
			try:
				return p.manager
			except AttributeError as err:
				raise AttributeError(self,'manager') from err

	def manager_present(self,mgr):
		"""\
			Do something when the object starts to be managed.
			The default is to do nothing.
			"""
		pass
	def _manager_present(self,mgr):
		self.manager_present(mgr)
		if isinstance(self,EtcDir):
			for v in self.values():
				p = getattr(v,_manager_present,None)
				if p is not None:
					p(mgr)

	def manager_gone(self):
		"""\
			Override me to do something when the object is no longer managed.
			The default is to do nothing.
			"""
		pass
	def _manager_gone(self):
		if isinstance(self,EtcDir):
			for v in self.values():
				p = getattr(v,_manager_gone,None)
				if p is not None:
					p()
		self.manager_gone()

class ManagedEtcDir(ManagedEtcThing):
	"""\
		A mix-in for the root of a managed tree.
		"""
	_mgr = None

	# The idea behind "manager" is that it's an object that is only strongly
	# referenced by the command which manages this here device. Thus the
	# manager will vanish (and the device will be notified about that) as
	# soon as the command terminates.
	#
	# The manager object must have a .drop_device() method which tells it
	# that a device is no longer under its control.
	#
	# .manager, when read, actually returns the controlling object directly.
	# 
	# The manager_lock (actually an asyncio.Event) allows you to wait for a
	# manager to start.
	# 
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self.manager_lock = asyncio.Event(loop=self._loop)

	@property
	def manager(self):
		m = self._mgr
		if m is not None:
			m = m()
		return m
	@manager.setter
	def manager(self,mgr):
		m = self._mgr
		if m is not None:
			m = m()
		if mgr is None:
			self._mgr = None
			self._manager_gone()
		else:
			assert m is None, "%s already has a manager: %s" % (self,m)
			self._manager_present(mgr)
	@manager.deleter
	def manager(self):
		if self._mgr is not None:
			self._manager_gone()

	def _manager_present(self,mgr):
		logger.debug("MGR %s set %s",self,mgr)
		self._mgr = ref(mgr,self._manager_gone)
		self.manager_lock.set()
		super()._manager_present(mgr)
	def _manager_gone(self):
		logger.debug("MGR %s del",self)
		self._mgr = None
		self.manager_lock.clear()
		super()._manager_gone()

	def has_update(self):
		super().has_update()
		mgr = self.manager
		if mgr is not None:
			self._manager_present(mgr)

#ManagedEtcDir.register('*', cls=ManagedEtcSubdir)
#ManagedEtcSubDir.register('*', cls=ManagedEtcSubdir)


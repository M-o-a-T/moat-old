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

from etcd_tree import EtcDir, EtcString, EtcBoolean

from moat.types.etcd import recEtcDir
from . import INFRA_DIR,INFRA

import logging
logger = logging.getLogger(__name__)


class InfraData(EtcDir):
	"""Type for /infra/HOSTNAME…/:host/data (specific) and /infra/:static/data (default)"""
	pass

class InfraPort(EtcDir):
	@property
	def essential(self):
		return self.get('essential',False)
	
	async def unlink(self):
		"""Disconnect this port."""
		h=self._get('host',None)
		p=self.get('port',None)
		if h and p:
			rh = await h.host['ports'][p]
			if rh.get('host','') == self.parent.parent.dnsname and rh.get('port','') == p:
				await rh.delete('port')
				await rh.delete('host')
		if h:
			await self.delete('host')
		if p:
			await self.delete('port')

	async def link(self,port):
		"""Connect this port to that. You can also pass in a destination
			host, in which case the remote side will not be affected."""
		await self.unlink()
		if isinstance(port,InfraPort):
			await port.unlink()

			await self.set('host',port.parent.parent.dnsname)
			await self.set('port',port.name)
			await port.set('host',self.parent.parent.dnsname)
			await port.set('port',self.name)
		else:
			await self.set('host',port.dnsname)

	@property
	def remote(self):
		return self._get('host').host['ports'][self['port']]

	@property
	def host(self):
		return self.parent.parent
		
class InfraPortHost(EtcString):
	"""Type for /infra/HOSTNAME…/:host/ports/NAME"""
	mark = False

	@property
	def host(self):
		t = self.root.lookup(INFRA_DIR)
		return t.lookup(reversed(self.value.split('.')), name=INFRA)

class InfraHost(recEtcDir,EtcDir):
	"""Type for /infra/HOSTNAME"""
	infra_path = None

	@property
	def dnsname(self):
		return ".".join(reversed(self.path[len(INFRA_DIR):-1]))

	async def children(self, depth=0, essential=False):
		"""List all possibly-essential children of a node, possibly at a certain depth.
			As a side effect, set .mark on all ports that reach any children,
			and set .infra_path on all results to the list of ports
			required to go there.
			"""
		seen = set()
		todo = [(self,())]
		res = []
		while todo:
			s,d = todo.pop(0)
			if s in seen:
				continue
			seen.add(s)
			if len(d) and depth in (0,len(d)):
				if not essential or s.essential:
					for x in d:
						x.mark = True
					s.infra_path = d
					res.append(s)
			try:
				ports = s['ports']
			except KeyError:
				pass
			else:
				for p in ports:
					p.mark = False
					try:
						h = await p['host'].host
					except KeyError:
						pass
					else:
						todo.append((h,d+(p,)))
		return res
	
	@property
	def essential(self):
		return self.get('essential',False)

InfraPort.register("host", cls=InfraPortHost, doc="refers to the host connected to this port")
InfraHost.register("ports","*", cls=InfraPort)
InfraHost.register("data", cls=InfraData)
InfraHost.register("essential", cls=EtcBoolean)

class InfraStatic(recEtcDir,EtcDir):
	"""Type for /infra/:static"""
	pass

InfraStatic.register("rsync", cls=EtcString, doc="source for rsync'ing additional content")
InfraStatic.register("data", cls=InfraData)


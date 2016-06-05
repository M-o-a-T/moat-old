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

import logging
logger = logging.getLogger(__name__)
from etcd_tree.node import EtcFloat,EtcInteger,EtcString

from . import OnewireDevice

class Onewire_2409(OnewireDevice):
	name = "switch"
	description = "main/aux switch"
	family = "1f"

	async def created(self):
		await super().created()

		server,path = self['path'].split(' ',1)
		srv = await self.root.lookup('bus','onewire',server,'bus')
		n = self.parent.parent.name+'.'+self.parent.name
		for sub in ('main','aux'):
			s = await srv.subdir("%s %s %s" % (path,n,sub))
			await s.set('broken',0, sync=False)
			await s.set('devices',{})

	async def deleted(self):
		import pdb;pdb.set_trace()
		await super().deleted()

		server,path = self['path'].split(' ',1)
		srv = await self.root.lookup('bus','onewire',server,'bus')
		n = self.parent.parent.name+'.'+self.parent.name
		keep = False
		for sub in ('main','aux'):
			try:
				s = await srv.subdir("%s %s %s" % (path,n,sub), create=False)
			except KeyError:
				continue
			v = await s.get('broken',99)
			if v < 3:
				await s.set('broken',v+1)
				keep = True
		if not keep:
			await srv.delete(n)


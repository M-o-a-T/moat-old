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

from collections.abc import Mapping,MutableMapping

class _NOT_HERE: pass
class _NOT_THERE: pass

def r_dict(m):
	if isinstance(m,Mapping):
		return dict((k,r_dict(v)) for k,v in m.items())
	else:
		return m

class OverlayDict(MutableMapping):
	def __init__(self,a,b):
		self.a = a
		self.b = b

	def __getitem__(self,k):
		if k in self.a:
			v = self.a[k]
			if v is _NOT_HERE:
				raise KeyError(k)
			if k in self.b:
				if type(v) is OverlayDict:
					v.b = self.b[k]
				elif isinstance(v,Mapping):
					self.a[k] = v = OverlayDict(v,self.b[k])
			elif type(v) is OverlayDict:
				v.b = {}
			return v
		elif k in self.b:
			v = self.b[k]
			if isinstance(v,Mapping):
				self.a[k] = v = OverlayDict({},v)
			return v
		raise KeyError(k)

	def __setitem__(self,k,v):
		self.a[k] = v

	def __delitem__(self,k):
		if k in self.b:
			if self.a.get(k,None) is not _NOT_HERE:
				self.a[k] = _NOT_HERE
		elif k not in self.a:
			raise KeyError(k)
	
	def __iter__(self):
		for k,v in self.a.items():
			if v is not _NOT_HERE:
				yield k
		for k in self.b:
			if k not in self.a:
				yield k

	def __len__(self):
		n=0
		for k,v in self.a.items():
			if v is not _NOT_HERE:
				n += 1
		for k in self.b:
			if self.a.get(k,None) is not _NOT_HERE:
				n += 1
		return n
	
	def __contains__(self,k):
		v = self.a.get(k,_NOT_THERE)
		if v is _NOT_HERE:
			return False
		if v is not _NOT_THERE:
			return True
		return k in self.b

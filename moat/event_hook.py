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

"""\
This code does basic configurable event mangling.

on switch *state livingroom *switch:
	send change $state lights livingroom $switch

on switch * * *:
	if neq $2 outside
	if state on alarm internal
	trigger alarm $2

Given the event "switch on livingroom main", this would cause a
"change on lights livingroom main" event if the internal alarm is off.
Otherwise a "alarm livingroom" would be triggered.

"""

import six

from moat.logging import log, TRACE
from moat.run import register_worker,unregister_worker,MIN_PRIO,MAX_PRIO
from moat.worker import Worker
from moat.base import Name
from moat.collect import Collection,Collected

onHandlers = {}
onHandlers2 = {}

class _OnHandlers(Collection):
	name = "on"

	def items(self):
		for i in sorted(self.keys(), key=lambda x:(self[x].prio,self[x].name)):
			yield i,self[i]

	def __getitem__(self,key):
		try:
			return super(_OnHandlers,self).__getitem__(key)
		except KeyError:
			if key in onHandlers:
				return onHandlers[key]
			if key in onHandlers2:
				return onHandlers2[key][0]
			if hasattr(key,"__len__") and len(key) == 1:
				if key[0] in onHandlers:
					return onHandlers[key[0]]
				if key[0] in onHandlers2:
					return onHandlers2[key[0]][0]
			raise

	def __setitem__(self,key,val):
		assert val.name==key, repr(val.name)+" != "+repr(key)
		onHandlers[val.id] = val
		try:
			onHandlers2[val.args].append(val)
		except KeyError:
			onHandlers2[val.args] = [val]
		super(_OnHandlers,self).__setitem__(key,val)
		register_worker(val)

	def __delitem__(self,key):
		val = self[key]
		unregister_worker(val)
		del onHandlers[val.id]
		onHandlers2[val.args].remove(val)
		if not onHandlers2[val.args]:
			del onHandlers2[val.args]
		super(_OnHandlers,self).__delitem__(val.name)

	def pop(self,key):
		val = self[key] if key else self.keys()[0]
		unregister_worker(val)
		del OnHandlers[val.id]
		try:
			del OnHandlers2[val.args]
		except KeyError:
			pass
		return val
OnHandlers = _OnHandlers()
OnHandlers.does("del")

class iWorker(Worker):
	"""This is a helper class, to pass the event name to Worker.__init__()"""
	def __init__(self):
		super(iWorker,self).__init__(self.name)

class OnEventBase(Collected,iWorker):
	"""Link an event to executing a MoaT block"""
	storage = OnHandlers.storage
	_simple = True

	def __init__(self, parent, args, name=None, prio=(MIN_PRIO+MAX_PRIO)//2+1):
		self.prio = prio
		self.displayname = name
		self.args = args
		self.parent = parent

		if name is None:
			name = Name("_on",self._get_id())
		super(OnEventBase,self).__init__(*name)
		for k in self.args:
			if hasattr(k,'startswith') and k.startswith('*'):
				self._simple = False

#		self.name = six.text_type(self.args)
#		if self.displayname is not None:
#			self.name += u" ‹"+" ".join(six.text_type(x) for x in self.displayname)+u"›"

		
		log(TRACE,"NewHandler",self.id)

	def does_event(self,event):
		if self._simple:
			return self.args == event
		ie = iter(event)
		ia = iter(self.args)
		ctx = {}
		pos = 0
		while True:
			try: e = six.next(ie)
			except StopIteration: e = StopIteration
			try: a = six.next(ia)
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return True
			if e is StopIteration or a is StopIteration:
				return False
			if hasattr(a,"startswith") and a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else:
					a = a[1:]
				ctx[a] = e
			elif str(a) != str(e):
				return False

#	def process(self, **k):
#		raise NotImplementedError("You need to implement 'process()' in %s" % (self.__class__.__name__,))

	def report(self, verbose=False):
		for r in super(OnEventBase,self).report(verbose):
			yield r
		if verbose:
			rep = getattr(self.parent,'report',None)
			if rep is not None:
				for r in rep(verbose):
					yield r

	def info(self):
		return u"%s (%d)" % (six.text_type(self.args),self.prio)

	def list(self):
		yield super(OnEventBase,self)
		yield("id",self.id)
		yield("prio",self.prio)
		if self.displayname is not None:
			yield("pname"," ".join(six.text_type(x) for x in self.displayname))
		yield("args",self.args)
		if hasattr(self.parent,"displaydoc"):
			yield("doc",self.parent.displaydoc)


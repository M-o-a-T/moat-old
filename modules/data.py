# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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

"""\
This code implements access to collections.

"""

from homevent.logging import log
from homevent.statement import Statement, main_words
from homevent.module import Module
from homevent.run import list_workers
from homevent.reactor import Events
from homevent.base import Name
from homevent.collect import get_collect,all_collect,Collection


class List(Statement):
	name=("list",)
	doc="list of / show details for various parts of the system"
	long_doc=u"""\
list
	shows all known types (but skips empty types)
list ‹type›
	shows a list of items of that type
list ‹type› ‹name…›
	shows details for that item
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		c = get_collect(event, allow_collection=True)
		try:
			if c is None:
				for m in all_collect(skip=True):
					print >>self.ctx.out, " ".join(m.name)
			elif isinstance(c,Collection):
				for n,m in c.iteritems():
					try:
						m = m.info
					except AttributeError:
						m = m.name
					else:
						if callable(m):
							m = m()
						if isinstance(m,basestring):
							m = m.split("\n")[0].strip()

					if isinstance(n,Name):
						n = u" ".join(unicode(x) for x in n)
					if m is not None:
						print >>self.ctx.out,u"%s :: %s" % (n,m)
					else:
						print >>self.ctx.out,u"%s" % (n,)
			else:
				for s,t in c.list():
					print >>self.ctx.out,"%s: %s" % (s,t)

		except Exception,e:
			print >>self.ctx.out, "* ERROR *",repr(e)
			
		finally:
			print >>self.ctx.out, "."


class Del(Statement):
	name=("del",)
	doc="delete a part of the system"
	long_doc=u"""\
del ‹type› ‹name…›
	remove that item
	-- see ‹list› 
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not event:
			for m in all_collect("del"):
				print >>self.ctx.out, " ".join(m.name)
			print >>self.ctx.out, "."
			return
		c = get_collect(event)
		if c is None:
			raise SyntaxError(u"Usage: del ‹type› ‹name…›")
		if not hasattr(c,"delete"):
			raise SyntaxError(u"You cannot delete those items.")
		return c.delete(ctx)


class DataModule(Module):
	"""\
		This module provides a couple of common data access functions.
		"""

	info = "provides a couple of common data access functions"

	def load(self):
		main_words.register_statement(List)
		main_words.register_statement(Del)
	
	def unload(self):
		main_words.unregister_statement(List)
		main_words.unregister_statement(Del)
	
init = DataModule

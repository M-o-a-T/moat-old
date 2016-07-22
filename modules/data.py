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
This code implements access to collections.

"""

import six

from datetime import datetime
import os

from moat import TESTING
from moat.logging import log
from moat.statement import Statement, main_words
from moat.module import Module
from moat.run import list_workers
from moat.reactor import Events
from moat.base import Name,flatten
from moat.twist import fix_exception,print_exception,log_wait
from moat.collect import get_collect,all_collect,Collection
from moat.times import humandelta,now
from moat.check import Check,register_condition,unregister_condition

from gevent import spawn
from gevent.queue import Queue

class List(Statement):
	name="list"
	doc="list of / show details for various parts of the system"
	long_doc=u"""\
list
	shows all known types (but skips empty types)
list ‹type›
	shows a list of items of that type
list ‹type› ‹name…›
	shows details for that item
list ‹type› *
	shows details for all items of that type
	
"""
	def run(self,ctx,**k):

		def out_one(c):
			for p,t in flatten((c,)):
				if isinstance(t,datetime):
					if TESTING and t.year != 2003:
						t = "%s" % (humandelta(t-now(t.year != 2003)),)
					else:
						t = "%s (%s)" % (humandelta(t-now(t.year != 2003)),t)
					if TESTING:
						lim = 3
					else:
						lim = 4
					ti = t.rfind('.')
					if ti>0 and len(t)-ti>lim and len(t)-ti<lim+6: # limit to msec
						t = t[:ti+lim]+")"

				elif isinstance(t,float):
					ft=float("%.4f"%t)
					if abs(ft-t)<0.00000001:
						t=ft
				print(p+u": "+six.text_type(t), file=self.ctx.out)

		event = self.params(ctx)
		c = get_collect(event, allow_collection=True)

		try:
			if c is None:
				for m in all_collect(skip=False):
					print(" ".join(m.name), file=self.ctx.out)
			elif isinstance(c,Collection):
				if event[-1] == "*":
					for m in c.items():
						print("* %s :: %s" % (n,m), file=self.ctx.out)
						out_one(m)
					return
				for n,m in c.items():
					try:
						m = m.info
					except AttributeError:
						m = m.name
					else:
						if callable(m):
							m = m()
						if isinstance(m,six.string_types):
							m = m.split("\n")[0].strip()

					if isinstance(n,Name):
						n = u" ".join(six.text_type(x) for x in n)
					if m is not None:
						print(u"%s :: %s" % (n,m), file=self.ctx.out)
					else:
						print(u"%s" % (n,), file=self.ctx.out)
			else:
				out_one(c)

		except Exception as e:
			fix_exception(e)
			print("* ERROR *",repr(e), file=self.ctx.out)
			print_exception(e,file=self.ctx.out)
		finally:
			print(".", file=self.ctx.out)

class Del(Statement):
	name="del"
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
				print(" ".join(m.name), file=self.ctx.out)
			print(".", file=self.ctx.out)
			return
		c = get_collect(event)
		if c is None:
			raise SyntaxError(u"Usage: del ‹type› ‹name…›")
		if not hasattr(c,"delete"):
			raise SyntaxError(u"You cannot delete those items.")
		return c.delete(ctx)

class VarCheck(Check):
	name="exists var"
	doc="Check if '$var' can be resolved"

	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (variable name)"
		return Name(*args) in self.ctx

class DataModule(Module):
	"""\
		This module provides a couple of common data access functions.
		"""

	info = "provides a couple of common data access functions"

	def load(self):
		main_words.register_statement(List)
		main_words.register_statement(Del)
		register_condition(VarCheck)
	
	def unload(self):
		main_words.unregister_statement(List)
		main_words.unregister_statement(Del)
		unregister_condition(VarCheck)
	
init = DataModule

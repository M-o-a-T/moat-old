# -*- coding: utf-8 -*-

##
##  Copyright © 2008-2012, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division

"""\
This code does basic timeout handling.

avg NAME...
	- creates an averaging handler
set avg VALUE NAME...
	- sets a value
var avg X NAME...
	- gets the current value

"""

from homevent.statement import Statement, main_words
from homevent.module import Module
from homevent.check import Check,register_condition,unregister_condition
from homevent.times import unixdelta, now, humandelta
from homevent.base import Name,SName
from homevent.collect import Collection,Collected

from datetime import timedelta

class Avgs(Collection):
    name = "avg"
Avgs = Avgs()
Avgs.does("del")


class Avg(Collected):
	"""This is the thing that averages."""
	storage = Avgs.storage

	value = None # last measurement
	last_tm = None # last time measurement was fed in
	total_tm = None
	avg = None # current average value

	def __init__(self,parent,name):
		self.ctx = parent.ctx
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		super(Avg,self).__init__(*name)

	def __repr__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name, self.avg)

	def _calc(self, mod=False):
		if self.last_tm is None:
			return None
		n = now()
		t = n-self.last_tm
		nt = self.total_tm+t
		nts = unixdelta(nt)
		if nts == 0: ## called right after init'ing
			r = self.value
		else:
			r = (self.avg*unixdelta(self.total_tm) + self.value*unixdelta(t)) / nts
		if mod:
			self.total_tm = nt
			self.avg = r
		return r

	def feed(self, value):
		if value is None:
			value = self.value
			if value is None:
				return
		if self.avg is None:
			self.avg = value
			self.total_tm = timedelta(0)
		else:
			self._calc(True)
		self.value = value
		self.last_tm = now()
		
	def list(self):
		yield ("name"," ".join(unicode(x) for x in self.name))
		yield ("cur_value",self.value)
		if self.last_tm is not None:
			yield ("last_time",self.last_tm)
			yield ("total_time",humandelta(self.total_tm))
			yield ("last_value",self.avg)
			yield ("value",self._calc())

	def info(self):
		if self.total_tm is None:
			return "(new)"
		return "%s %s" % (self._calc(), unixdelta(self.total_tm))
	
	def delete(self,ctx=None):
		self.delete_done()


class AvgHandler(Statement):
	name="avg"
	doc="An average-value accumulator."
	long_doc=u"""\
avg ‹name…›
	- An average-value accumulator.
      You feed it with "set avg" statements.
	"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		Avg(self, SName(event))

	
class AvgSet(Statement):
	name="set avg"
	doc="feed a value to an averager"
	long_doc="""\
set avg VALUE NAME
	Sends the value to this named averager.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u"Usage: set avg ‹value› ‹name…›")
		m = Avgs[Name(*event[1:])]
		m.feed(float(event[0]))

class ExistsAvgCheck(Check):
	name="exists avg"
	doc="check if an averager exists"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists avg ‹name…›")
		name = Name(*args)
		return name in Avgs

class VarAvgHandler(Statement):
	name="var avg"
	doc="assign a variable to the current value of an averager"
	long_doc=u"""\
var avg NAME name...
	: $NAME contains the current value of that averager.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(*event[1:])
		setattr(self.parent.ctx,var,Avgs[name]._calc())


class AvgModule(Module):
	"""\
		This module contains a handler for computing average values.
		"""

	info = "Average values over time"

	def load(self):
		main_words.register_statement(AvgHandler)
		main_words.register_statement(AvgSet)
		main_words.register_statement(VarAvgHandler)
		register_condition(ExistsAvgCheck)
	
	def unload(self):
		main_words.unregister_statement(AvgHandler)
		main_words.unregister_statement(AvgSet)
		main_words.unregister_statement(VarAvgHandler)
		unregister_condition(ExistsAvgCheck)

init = AvgModule

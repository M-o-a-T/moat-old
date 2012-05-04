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

from homevent.statement import Statement, main_words, AttributedStatement
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
	"""This is the thing that averages over time."""
	storage = Avgs.storage

	doc="?not set"
	params = (0,0)
	mode = None # "?not set"

	def reset(self):
		self.value = None # last measurement
		self.value_tm = None # last time measurement was fed in
		self.prev_value = None
		self.total_tm = None
		self.total_samples = 0
		self.avg = None # current average value

	def weigth(self, mod=False):
		"""Value of the 'new' sample"""
		raise NotImplementedError("no sample weight formula")

	def __init__(self,parent,name):
		self.ctx = parent.ctx
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		super(Avg,self).__init__(*name)
		self.reset()

	def __repr__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name, self.avg)

	def _calc(self, mod=False):
		raise NotImplementedError("You need to implement the actual calculation in %s" % (self.__class__.__name__,))

	def feed(self, value):
		self.prev_value = self.value
		if value is None:
			value = self.value
			if value is None:
				return
		self.value = value
		self.value_tm = now()
		self.total_samples += 1
		self.avg = self._calc(True)
		
	def list(self):
		yield ("name"," ".join(unicode(x) for x in self.name))
		yield ("mode",self.mode)
		yield ("value",self.value)
		if self.value_tm is not None:
			yield ("set time",self.value_tm)
			yield ("prev value",self.prev_value)
			yield ("total time",self.total_tm)
			yield ("total samples",self.total_samples)
			yield ("current average",self._calc())

	def info(self):
		if self.total_tm is None:
			return "(new)"
		return "%s %s" % (self._calc(), unixdelta(self.total_tm))
	
	def delete(self,ctx=None):
		self.delete_done()

class TimeAvg(Avg):
	"""This is the thing that averages over time."""
	mode = "time"
	doc="Time-based equal-weight"

	def weigth(self, mod=False):
		if self.value_tm is None:
			return None
		n = now()
		t = n-self.value_tm
		nt = self.total_tm+t
		nts = unixdelta(nt)
		if mod:
			self.total_tm = nt
		if nts == 0: ## called right after init'ing
			return 0
		else:
			return unixdelta(t) / nts

	def _calc(self, mod=False):
		w = self.weigth(mod)
		if w is None:
			return None
		if w == 0:
			return self.avg
		
		r = self.avg*(1-w) + self.value*w
		if mod:
			self.avg = r
		return r

	def feed(self, value):
		"""Store the new value but calculate over the previous ones."""
		self.prev_value = self.value
		self.total_samples += 1
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
		self.value_tm = now()
		
class DecayTimeAvg(TimeAvg):
	"""Decaying average, time-based weight"""
	mode="decaytime"
	doc="Time-based decay; param: weight of one sampled minute"
	params = (1,1)

	def __init__(self,parent,name, weight):
		super(DecayTimeAvg,self).__init__(parent,name)
		# Calculations are second-based, but the user parameter is per minute.
		self.p = 1-(1-float(weight))**(1/60)

	def weigth(self, mod=False):
		if self.value_tm is None:
			return None
		t = now()-self.value_tm
		nt = unixdelta(t)
		if nt == 0: ## called right after init'ing
			return 0
		else:
			return 1-(1-self.p)**nt

	def list(self):
		for r in super(DecayTimeAvg,self).list():
			yield r
		yield ("weight/hour",1-(1-self.p)**3600)
		yield ("weight/minute",1-(1-self.p)**60)
		yield ("weight/second",self.p)


class DecaySamplesAvg(Avg):
	"""Decaying average, sample-based weight"""
	mode="decay"
	doc="Samples-based decay; param: weight of one sample"
	params = (1,1)

	def __init__(self,parent,name, weight):
		super(DecaySamplesAvg,self).__init__(parent,name)
		self.p = float(weight)

	def _calc(self, mod=False):
		if self.avg is None:
			return self.value
		if not mod:
			return self.avg
		r = self.avg*(1-self.p) + self.value*self.p
		if mod:
			self.avg = r
		return r

	def list(self):
		for r in super(DecaySamplesAvg,self).list():
			yield r
		yield ("weight",self.p)


class MovingSamplesAvg(Avg):
	"""Moving average, based on the last N values"""
	mode="moving"
	doc="Moving average; param: number of samples"
	params = (1,1)

	def __init__(self,parent,name, samples):
		super(MovingSamplesAvg,self).__init__(parent,name)
		self.n = int(samples)
		self.values = []

	def _calc(self, mod=False):
		if not mod:
			return self.avg

		self.values.append(self.value)
		if len(self.values) > self.n:
			old_value = self.values.pop(0)
			q = 1/self.n
			avg = (self.avg-old_value*q)/(1-q)
		else:
			q = 1/len(self.values)
			avg = self.avg

		if self.avg is None:
			self.avg = self.value
		else:
			self.avg = avg*(1-q)+self.value*q
		return self.avg

	def list(self):
		for r in super(MovingSamplesAvg,self).list():
			yield r
		yield ("samples",len(self.values))
		yield ("max samples",self.n)
		if len(self.values) < 7:
			r = range(len(self.values))
		else:
			r = range(3)+range(len(self.values)-3,len(self.values))
		for i in r:
			yield ("sample "+str(i),self.values[i])


modes = {}

class AvgHandler(AttributedStatement):
	name="avg"
	doc="An average-value accumulator."
	avg = TimeAvg
	settings = ()
	long_doc=u"""\
avg ‹name…›
	- An average-value accumulator.
      You feed it with "set avg" statements.
Known modes (default: %s):
""" % (avg.mode,)

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.avg(self, SName(event), *self.settings)


@AvgHandler.register_statement
class AvgMode(Statement):
	name="mode"
	doc="change the mode"
	long_doc=u"""\
mode ‹name› ‹param…› - set how to calculate the mode
"""
	def run(self,ctx):
		event = self.params(ctx)
		avg = modes[event[0]]
		args = event[1:]
		if len(args) < avg.params[0] or len(args) > avg.params[1]:
			if avg.params[0] == avg.params[1]:
				raise SyntaxError(u"‹mode %s› requires %d params, got %d" % (avg.mode,avg.params[0],len(args)))
			else:
				raise SyntaxError(u"‹mode %s› requires between %d and %d params, got %d" % (avg.mode,avg.params[0],avg.params[1],len(args)))
		self.parent.avg = avg
		self.parent.settings = args
		
	
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

class AvgReset(Statement):
	name="reset avg"
	doc="Re-initialize an averager"
	long_doc="""\
reset avg NAME
	Clear the averager's history.
	
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

class VarAvgHandler(AttributedStatement):
	name="var avg"
	doc="assign a variable to the current value of an averager"
	long_doc=u"""\
var avg NAME name...
	: $NAME contains the current value of that averager.
"""
	src = None
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(*event[1:])
		if self.src is None:
			value = Avgs[name]._calc()
		else:
			value = getattr(Avgs[name],self.src)
		setattr(self.parent.ctx,var,value)

@VarAvgHandler.register_statement
class AvgVarUse(Statement):
	name="use"
	doc="change which variable to use"
	avail = "value value_tm prev_value total_samples".split()
	long_doc=u"""\
use ‹var› - use some other value than the current average
Available: %s
""" % " ".join(avail)
	def run(self,ctx):
		event = self.params(ctx)
		if len(event) != 1 or event[0] not in self.avail:
			raise SyntaxError(u"‹use› requires a parameter: " + u"¦".join(self.avail))
		self.parent.src = event[0]


class AvgModule(Module):
	"""\
		This module contains a handler for computing average values.
		"""

	info = "Average values over time"

	def load(self):
		mlen=0
		for v in globals().itervalues():
			m = getattr(v,"mode",None)
			if m is None: continue
			modes[m] = v
			if mlen < len(m): mlen = len(m)
		for v in modes.itervalues():
			AvgHandler.long_doc += v.mode+" "*(mlen-len(v.mode)+1)+v.doc+"\n"

		main_words.register_statement(AvgHandler)
		main_words.register_statement(AvgSet)
		main_words.register_statement(AvgReset)
		main_words.register_statement(VarAvgHandler)
		register_condition(ExistsAvgCheck)
	
	def unload(self):
		main_words.unregister_statement(AvgHandler)
		main_words.unregister_statement(AvgSet)
		main_words.unregister_statement(AvgReset)
		main_words.unregister_statement(VarAvgHandler)
		unregister_condition(ExistsAvgCheck)

init = AvgModule

# -*- coding: utf-8 -*-

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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
This code implements pulse-code modulation.

pwm NAME...:
	scale 0.5
	limit off 1 15
	limit on 0 20

set pwm $VALUE NAME...

"""

from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words, HelpSub
from homevent.event import Event
from homevent.run import process_event,register_worker,unregister_worker,\
	simple_event,process_failure
from homevent.reactor import shutdown_event
from homevent.module import Module
from homevent.worker import HaltSequence,ExcWorker
from homevent.times import simple_time_delta, now, humandelta
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name,SYS_PRIO
from homevent.twist import callLater, fix_exception
from homevent.collect import Collection,Collected

import os
import datetime as dt

timer_nr = 0

class PWMs(Collection):
	name = "pwm"
PWMs = PWMs()
PWMs.does("del")


class PWMError(RuntimeError):
	def __init__(self,w):
		self.PWM = w
	def __str__(self):
		return self.text % (" ".join(str(x) for x in self.PWM.name),)
	def __unicode__(self):
		return self.text % (" ".join(unicode(x) for x in self.PWM.name),)

class CommonPM(Collected):
	"""This is the (generic) thing that modulates."""
	storage = PWMs.storage

	type=None # override me!
	_value = None # current level we try to maintain
	timer = None # when to switch away next
	last = None # when last switched
	next = None # when switched next, i.e. timer expires
	t_off = None # pre-calculated L value
	t_on = None # pre-calculated H value
	state = None
	states = ("off","on")
	over = None # override

	def __init__(self,parent,name, names=("off","on"), **k):
		self.ctx = parent.ctx
		self.start = now()
		self.names = names
		for a,b in k.iteritems(): self.arg(a,b)
		self.validate()
		super(CommonPM,self).__init__(*name)
	
	def validate(self):
		pass

	def list(self):
		n=now()
		yield ("type",self.type)
		yield ("name"," ".join(unicode(x) for x in self.name))
		if self.state is not None:
			yield ("state",self.names[self.state])
		if self._value is not None:
			yield ("current",self._value)
		if self.last is not None:
			yield ("last",humandelta(n-self.last))
		if self.next is not None:
			yield ("next",humandelta(self.next-n))
		if self.t_off is not None:
			yield ("t_off",humandelta(self.t_off))
		if self.t_on is not None:
			yield ("t_on",humandelta(self.t_on))

	def info(self):
		if self._value is None or self.t_on is None:
			return "(new)"
		return "%f %s / %s" % (self._value,humandelta(self.t_on),humandelta(self.t_off))

	def delete(self,ctx):
		if self.timer:
			self.timer.cancel()
			self.timer = None
		try:
			if self.state:
				process_event(Event(self.ctx,"pcm","set",self.names[0],*self.name))
		except Exception as ex:
			fix_exception(ex)
			process_failure(ex)
		finally:
			self.delete_done()

	def __repr__(self):
		return u"‹%s %s %d›" % (self.__class__.__name__, self.name,self._value)

	def arg(self,key,value):
		raise SyntaxError(u"PWM ‹%s› doesn't understand ‹%s›" % (self.type, key))
		
	def new_value(self,val):
		"""Calculate+return new values for t_off and t_on"""
		raise NotImplementedError("You need to override new_value()")

	def do_timed_switch(self):
		self.timer = None
		d = self.do_switch()
		d.addErrback(process_failure)

	def do_switch(self):
		"""Click"""
		if self.state:
			self.state = 0
			tn = self.t_off
		else:
			self.state = 1
			tn = self.t_on

		process_event(Event(self.ctx,"pcm","set",self.names[self.state],*self.name))
		try:
			self.last = self.next
			if tn is not None:
				self.next = self.last + dt.timedelta(0,tn)
				self.timer = callLater(False,self.next,self.do_timed_switch)
			else:
				self.next = None
		except Exception as e:
			fix_exception(e)
			process_failure(e)
			simple_event(self.ctx,"pcm","error",*self.name)
		
	def get_value(self):
		return self._value
	def set_value(self,val=None):
		if val is None: val = self._value
		assert 0<=val<=1, u"Value is '%s', not in 0…1" % (val,)

		do = self.t_on if self.state else self.t_off
		self.t_off,self.t_on = self.new_value(val)
		dn = self.t_on if self.state else self.t_off

		self._value = val

		if do != dn:
			if self.timer is not None:
				self.timer.cancel()
			if dn is not None:
				self.next = (self.last if self.last is not None else now()) + dt.timedelta(0,dn)
				self.timer = callLater(False,self.next,self.do_timed_switch)
	value = property(get_value,set_value)

	
class StdPWM(CommonPM):
	doc="almost-constant period"
	long_doc="""\
A standard pulse width-modulated signal with mostly-constant period
"""
	type="PWM"
	interval=None

	def validate(self):
		super(StdPWM,self).validate()
		if self.interval is None:
			raise SyntaxError(u'Usage: pwm ‹name…›: type %s: requires ‹interval›' % (self.type,))

	def arg(self,k,v):
		if k == "interval":
			self.interval = v
		else:
			super(StdPCM,self).arg(k,v)

	def new_value(self,val):
		if val == 0: return (None,0) # off
		if val == 1: return (0,None) # on

		return (self.interval * (1-val), self.interval * val)


class StdPDM(StdPWM):
	doc="constant 'on' time'"
	long_doc="""\
A pulse density modulated signal with constant 'on' time
"""
	type="PDM"
	interval=None

	def new_value(self,val):
		if val == 0: return (None,0) # off
		if val == 1: return (0,None) # on

		return (self.interval * (1-val)/val, self.interval)

class InvPDM(StdPWM):
	doc="constant 'off' time"
	long_doc="""\
A pulse density modulated signal with constant 'off' time
"""
	type="iPDM"
	interval=None

	def new_value(self,val):
		if val == 0: return (None,0) # off
		if val == 1: return (0,None) # on

		return (self.interval, self.interval * val/(1-val))



class PWMHandler(AttributedStatement):
	name=("pwm",)
	doc="create a pulse-width handler"
	long_doc=u"""\
pwm NAME…: type 
	- create a pulse-width modulator
	  This modulator translates a floating-point value to a periodic
      on/off event whose duty cycle equals that value.
"""
	pwm = None

	def __init__(self,*a,**k):
		self.attrs = {}
		super(PWMHandler,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: pwm ‹name…›')
		if self.pwm is None:
			raise SyntaxError(u'Usage: pwm ‹name…›: requires ‹type›')

		self.pwm(self,Name(event), **self.attrs)

PWMtypes = {}
v = None
for v in globals().itervalues():
	try:
		if issubclass(v,CommonPM) and v.type is not None:
			PWMtypes[Name(v.type)] = v
	except TypeError: pass
del v
		
class PWMtype(Statement,HelpSub):
	helpsub = PWMtypes
	helpsubname = "type"

	name = ("type",)
	doc = "specify the kind of PWM"
	long_doc=u"""\
type ‹kind›
	- specify which type of modulator you want
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: type ‹kind›')
		self.parent.pwm = PWMtypes[Name(event)]
PWMHandler.register_statement(PWMtype)
	

class PWMinterval(Statement):
	name = ("interval",)
	doc = "specify the timing base for a PWM controller"
	long_doc=u"""\
interval ‹timespec›
	- specify how long the base interval should be
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: interval ‹timespec›')

		self.parent.attrs["interval"] = simple_time_delta(event[:])
PWMHandler.register_statement(PWMinterval)
	

class PWMUpdate(AttributedStatement):
	name = ("update","pwm")
	doc = "change the parameters of an existing PWM controller"
	long_doc="""\
This statement updates the parameters of a PWM controller.
"""
	def __init__(self,*a,**k):
		self.attrs = {}
		super(PWMUpdate,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError('Usage: update pwm ‹name…›')
		if not attrs:
			raise SyntaxError('Usage: update pwm ‹name…›: no attributes given')
		
		pwm = PWMs[Name[event]]
		for a,b in self.attrs.iteritems():
			pwm.arg(a,b)
		pwm.validate()
		pwm.set_value(None)
PWMUpdate.register_statement(PWMinterval)


class PWMSet(Statement):
	name = ("set","pwm")
	doc = "change the destination value of an existing PWM controller"
	long_doc="""\
This statement sets a PWM controller's value.
The PWM will not do anything before you do that.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError('Usage: set pwm ‹value› ‹name…›')
		
		pwm = PWMs[Name(event[1:])]
		pwm.value = float(event[0])


class ExistsPWMCheck(Check):
	name=("exists","pwm")
	doc="check if a PWM controller exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists pwm ‹name…›")
		name = Name(args)
		return name in PWMs

class OnPWMCheck(Check):
	name=("pwm",)
	doc="check if a PWM is turned on"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if pwm ‹name…›")
		name = Name(args)
		return PWMs[name].state


class VarPWMHandler(Statement):
	name=("var","pwm")
	doc="assign a variable to the PWM's value"
	long_doc=u"""\
var pwm NAME name...
	: $NAME contains the PWM controller's set goal
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(event[1:])
		setattr(self.parent.ctx,var,PWMs[name].value)


class Shutdown_Worker_PWM(ExcWorker):
	"""\
		This worker turns off all PWMs.
		"""
	prio = SYS_PRIO+4

	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self, **k):
		super(Shutdown_Worker_PWM,self).process(**k)
		for p in PWMs.values():
			pwm.set_value(0)

	def report(self,*a,**k):
		return ()


class PWMModule(Module):
	"""\
		This module contains controllers for PWMs.
		"""

	info = "controllers for pulse-width modulation"
	worker = Shutdown_Worker_PWM("PWM killer")

	def load(self):
		main_words.register_statement(PWMHandler)
		main_words.register_statement(PWMUpdate)
		main_words.register_statement(PWMSet)
		main_words.register_statement(VarPWMHandler)
		register_condition(ExistsPWMCheck)
		register_condition(OnPWMCheck)
		register_worker(self.worker)
	
	def unload(self):
		main_words.unregister_statement(PWMHandler)
		main_words.unregister_statement(PWMUpdate)
		main_words.unregister_statement(PWMSet)
		main_words.unregister_statement(VarPWMHandler)
		unregister_condition(ExistsPWMCheck)
		unregister_condition(OnPWMCheck)
		unregister_worker(self.worker)

init = PWMModule

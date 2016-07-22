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
This code handles the MoaT device

"""

import six

from moat.module import Module
from moat.base import Name,SName
from moat.logging import log,DEBUG,TRACE,INFO,WARN
from moat.statement import Statement, main_words, AttributedStatement
from moat.check import Check,register_condition,unregister_condition
from moat.onewire import connect,disconnect, devices
from moat.net import NetConnect
from moat.monitor import Monitor,MonitorHandler, MonitorAgain
from moat.in_out import register_input,register_output, unregister_input,unregister_output, Input,Output, BoolIO
from moat.times import humandelta,now
from moat.twist import fix_exception,Jobber
from moat.run import simple_event, process_failure
from moat.collect import Collection,Collected
from moat.delay import DelayFor
from moat.event_hook import OnEventBase
from weakref import WeakValueDictionary

import struct
from gevent import sleep

MOAT_EVENT_NAME=Name('moat','onewire','devices')

class Moats(Collection):
        name = "moat device"
Moats = Moats()
Moats.does("del")
moat_ids = WeakValueDictionary()

def moat_key(k):
	if len(k)>1 and isinstance(k[-1],six.integer_types):
		k = tuple(k[:-2])+(k[-2]+'.'+str(k[-1]),)
	return k

class Moat(Collected,Jobber):
	"""Abstraction representing one MoaT device"""
	storage = Moats.storage
	worker = None
	alarmed = True
	event_on = None
	event_off = None

	def __init__(self,name,dev):
		self.dev = dev
		super(Moat,self).__init__(name)
		self.start_job("worker",self._worker)
		self.event_on = MoatAlarmOnEvent(self,dev)
		self.event_off = MoatAlarmOffEvent(self,dev)
		moat_ids[dev] = self
	
	def list(self):
		yield super(Moat,self)
		dev = devices.get(self.dev,None)
		if dev:
			yield ("device",dev)
		else: # vanished
			yield ("id",dev)
	
	def delete(self):
		if self.event_on:
			self.event_on.delete()
		if self.event_off:
			self.event_off.delete()
		self.stop_job('worker')
		super(Moat,self).delete()

	def alarm_on(self):
		self.alarmed = True
		if not self.worker:
			self.start_job("worker",self._worker)

	def alarm_off(self):
		pass

	def __getitem__(self,k):
		return devices[self.dev].get(moat_key(k))
	def __setitem__(self,k,v):
		return devices[self.dev].set(moat_key(k),v)

	def tell(self, s,i):
		d = self['%s.%s' % (s,i)]
		if d != "":
			simple_event('moat','update',self.name, s,i, value=d,name=self.name,subsys=s,part=i)

	def _worker(self):
		dx = 0.1
		while True:
			if not self.alarmed:
				return
			try:
				src = self['alarm/sources']
				if not src:
					self.alarmed = False
					return
				for s in src.split(','):
					si = self['alarm/'+s]
					if not si:
						continue # somebody else beat us to it
					if isinstance(si,six.integer_types):
						si = (str(si),)
					else:
						si = si.split(',')
					for i in si:
						if s == "console":
							if i != 1:
								simple_event('moat','alarm',self.name,'error','console',i)
							cons = self['console']
							if cons != "":
								simple_event('moat',self.name,'console', data=cons)
	
						elif s == "status":
							simple_event('moat',self.name,'status', i, value=self['status/'+i])
	
						else:
							self.tell(s,i)
			except (DisconnectedError,TimedOut) as e:
				fix_exception(e)
				process_failure(e)
				dx = 30
				
			sleep(dx)
			dx *= 1.5
			if dx > 3:
				dx = 3
		
_new_moat_ev = None
class NewMoatEvent(OnEventBase):
	"""triggers when a new bus device shows up"""
	def __init__(self):
		super(NewMoatEvent,self).__init__(parent=None, args=Name('onewire','device','new','*'), name=MOAT_EVENT_NAME)

	def process(self, event,**k):
		dev = event.ctx.id
		if not dev.startswith('f0.'):
			return
		name = devices[dev].get('config/name')
		seq = 0
		n = name
		while n in Moats:
			if Moats[n].dev == dev:
				return # dup
			seq += 1
			n = "%s.%d" % (name,seq)
		Moat(name=n,dev=dev)
		simple_event(event.ctx, "moat","new",n, dev=dev)

class MoatAlarmOnEvent(OnEventBase):
	"""triggers when a new bus device shows up"""
	def __init__(self,parent,dev):
		super(MoatAlarmOnEvent,self).__init__(parent=parent, args=Name('onewire','alarm','on',dev), name=Name('moat','alarm','on',dev))

	def process(self, event,**k):
		dev = event.ctx.id
		m = moat_ids[dev]
		if m is not None:
			m.alarm_on()

class MoatAlarmOffEvent(OnEventBase):
	"""triggers when a new bus device shows up"""
	def __init__(self,parent,dev):
		super(MoatAlarmOffEvent,self).__init__(parent=parent, args=Name('onewire','alarm','off',dev), name=Name('moat','alarm','off',dev))

	def process(self, event,**k):
		dev = event.ctx.id
		m = moat_ids[dev]
		if m is not None:
			m.alarm_off()

class MOATio(object):
	"""Base class for Wago input and output variables"""
	typ="moat port"
	def __init__(self, name, params,addons,ranges,values):
		if len(params) != 2:
			raise SyntaxError(u"Usage: %s moat ‹devname› ‹port›"%(self.what,))
		self.dev = params[0]
		self.nr = int(params[1])
		super(MOATio,self).__init__(name, params,addons,ranges,values)

	def list(self):
		yield super(MOATio,self)
		yield ("device",self.dev)
		yield ("port",self.port)

class MOATinport(BoolIO,MOATio,Input):
	what="input"
	doc="A MoaT port used as input"
	long_doc="""\
moat name portnr
	: Device ‹name›'s port ‹portnr› is read from the bus.
"""
	def _read(self):
		val = Moats[self.dev][('port',self.nr)]
		return val

class MOATadc(MOATio,Input):
	what="input"
	typ="moat adc"
	doc="A MoaT A/D converter"
	long_doc="""\
moat adc nr
	: Device ‹name›'s ADC ‹nr› is read from the bus.
"""
	def _read(self):
		val = Moats[self.dev][('adc',self.nr)]
		return val

class MOAToutport(BoolIO,MOATio,Output):
	what="output"
	typ="moat port"
	doc="An output which changes a MoaT port"
	long_doc="""\
moat name portnr
	: Device ‹name›'s port ‹portnr› is written to the bus.
"""
	def _write(self,val):
		Moats[self.dev][('port',self.nr)] = int(val)

class MOATset(Statement):
	name="set moat"
	doc="send a value to a MoaT device"
	long_doc=u"""\
set moat NAME VALUE attr…
	: ‹VALUE› is written to device ‹dev›'s attribute ‹attr›.
	  This is a one-shot version of ‹output X moat DEV ATTR› plus ‹set output VALUE X›.
	  ‹attr› can be two words (like "port 1" or "status reboot").
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3 or len(event) > 4:
			raise SyntaxError("Usage: set moat VALUE DEVICE ATTRIBUTE")
		name, val = event[0:2]
		try:
			attr = int(event[3])
		except ValueError:
			attr = "%s/%s" % event[2:4]
		except IndexError:
			attr = event[2]
		else:
			attr = "%s.%d" % (event[2],attr)
		dev = dev.lower()
		
		Moats[name][attr] = val

class MOATmodule(Module):
	"""\
		Basic moat access.
		"""

	info = "Basic one-wire access"

	def load(self):
		global _new_moat_ev
		_new_moat_ev = NewMoatEvent()
		main_words.register_statement(MOATset)
		register_input(MOATinport)
		register_input(MOATadc)
		register_output(MOAToutport)
	
	def unload(self):
		if _new_moat_ev is not None:
			_new_moat_ev.delete()
		main_words.unregister_statement(MOATset)
		unregister_input(MOATinport)
		unregister_input(MOATadc)
		unregister_output(MOAToutport)
	
init = MOATmodule

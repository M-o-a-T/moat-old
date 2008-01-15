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
This code implements basic commands to access FS20 switches.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement,Statement, main_words, \
	ComplexStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import simple_event
from homevent.event import Event
from homevent.context import Context
from homevent.base import Name

from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
from homevent.fs20 import handler,register_handler,unregister_handler, \
	from_hc, from_dev, to_hc, to_dev
from homevent.fs20sw import group

codes = {}
codenames = {}
devs = {}
devnames = {}

switch_codes = {
	"off": 0x00,
	"level01" : 0x01,
	"level02" : 0x02,
	"level03" : 0x03,
	"level04" : 0x04,
	"level05" : 0x05,
	"level06" : 0x06,
	"level07" : 0x07,
	"level08" : 0x08,
	"level09" : 0x09,
	"level10" : 0x0A,
	"level11" : 0x0B,
	"level12" : 0x0C,
	"level13" : 0x0D,
	"level14" : 0x0E,
	"level15" : 0x0F,
	"full" : 0x10, # alias level16
	"on" : 0x11, # old value
	"toggle" : 0x12, # between "off" and "on / last value"
	"dim_up" : 0x13,
	"dim_down" : 0x14,
	"dim_updown" : 0x15, # up, wait, down, wait, ... essentially unknown
	"timer_set" : 0x16, # timer programming
	"status" : 0x17, # assuming that the thing can reply!
	"timer_off" : 0x18,
	"timer_full" : 0x19, # 100%
	"timer_on" : 0x1a, # last value
	"reset" : 0x1b, # factory state

	"dim": None, # catch-all for dimming
	"timer": None, # catch-all for timer control
}

switch_names = {}
for a,b in switch_codes.iteritems():
	if b is not None:
		switch_names[b]=a

class CannotDoError(RuntimeError):
	"""can't do this thing"""
	def __init__(self,switch,what):
		self.switch = switch
		self.what = what
	def __unicode__(self):
		return u"%s cannot do ‹%s›" % (unicode(self.switch), self.what)
		

class SwitchGroup(group):
	"""\
	Switches which share a house code.
	"""
	def __init__(self,code,name):
		super(SwitchGroup,self).__init__(code,6)
		self.code = code
		self.name = Name(name)
		self.devs = {}
		self.last_dgram = None

	def add(self):
		if self.code in codes:
			raise RuntimeError("Device exists (%s)" % (to_hc(self.code),))
		if self.name in codenames:
			raise RuntimeError("Device exists (%s)" % (self.name,))

		codes[self.code] = self
		codenames[self.name] = self

	def delete(self):
		del codes[self.code]
		del codenames[self.name]

	def __unicode__(self):
		return u"FS20_SwitchGroup ‹%s›" % (self.name,)

	def __repr__(self):
		try:
			return u"‹%s:%s:%s›" % (self.__class__.__name__, to_hc(self.code), self.name)
		except Exception:
			return "‹"+self.__class__.__name__+"›"
	
	def add_switch(self,switch):
		dc = to_hc(switch.code)
#		if dc % 100 == 44 or dc // 100 == 44:
#			raise SyntaxError("Devices cannot have group or master codes")
		if switch.code in self.devs:
			raise RuntimeError("Device exists (%s in %s)" % (unicode(self.codes[switch.code]), unicode(self)))

		self.devs[switch.code] = switch

	def datagramReceived(self,data, handler=None, timedelta=None):
		if len(data) < 2: raise WrongDatagram

		if self.last_dgram is not None and timedelta is not None and \
				self.last_dgram == data and timedelta < 0.15:
			return
		self.last_dgram = data

		fcode = ord(data[1])
		if fcode & 0x20:
			if len(data) != 3: raise WrongDatagram
			ext = ord(data[2])
		else:
			if len(data) != 2: raise WrongDatagram
			ext = None

		dc = ord(data[0])
		try:
			dev = self.devs[dc]
		except KeyError:
			simple_event(Context(), "fs20","unknown","device", to_hc(self.code), to_dev(dc), "".join("%02x" % ord(x) for x in data))
			return
		else:
			try:
				fn = switch_names[fcode & 0x1F]
			except KeyError:
				simple_event(Context(), "fs20","unknown","function", to_hc(self.code), fcode & 0x1F, "".join("%02x" % ord(x) for x in data))
				return

			if fcode & 0x80:
				hdl = dev.getReply
			else:
				hdl = dev.get
			if ext is not None:
				res = defer.maybeDeferred(hdl,fn,ext,handler=handler)
			else:
				res = defer.maybeDeferred(hdl,fn,handler=handler)

		def send_cpl(_):
			data = chr(dc)+chr(fcode|0x80)+data[2:]
			self.send(data, handler)
			return _
		if fcode & 0x40:
			res.addCallback(send_cpl)

		return res


class Switch(object):
	"""\
	This is the internal representation of a single fs20-addressable
	switch, dimmer, or similar entity.
	
	Note that at this time, no internal state is stored by this module.
	If needed, you'll have to do that yourself.
	"""
	def __init__(self,code,name, parent=None, handler=None, can_do = None, init = None):
		self.parent = parent
		self.code = code
		self.name = Name(name)
		self.handler = handler
		self.does = set(can_do) if can_do is not None else set(("on","off"))
		self.state = None
		self.ext = None
	
	def add(self):
		if not self.parent:
			raise RuntimeError("no parent set")
		if self.code in self.parent.devs:
			raise RuntimeError("duplicate code")
		if self.name in devnames:
			raise RuntimeError("duplicate name")

		self.parent.add_switch(self)
		devnames[self.name] = self

	def delete(self):
		del self.parent.devs[self.code]
		del devnames[self.name]

	def __unicode__(self):
		return u"FS20_Switch ‹%s›" % (self.name,)

	def __repr__(self):
		try:
			return u"‹%s:%s:%s›" % (self.__class__.__name__, self.name,self.parent.name)
		except Exception:
			return "‹"+self.__class__.__name__+"›"
		
	def can_do(self, *things):
		for thing in things:
			if thing not in switch_codes:
				raise SyntaxError(u"‹%s› is not something a FS20 switch knows about." % (thing,))
			self.does.add(thing)

	def cannot_do(self, *things):
		for thing in things:
			if thing not in switch_codes:
				raise SyntaxError(u"‹%s› is not something a FS20 switch knows about." % (thing,))
			self.does.remove(thing)
	
	def _allowed(self, what):
		if what.startswith("dim_") and "dim" in self.does:
			return True
		elif what.startswith("timer_") and "timer" in self.does:
			return True
		else:
			return what in self.does

	def set(self, state, ext=None, force=False):
		if not self._allowed(state):
			raise CannotDoError(self,state)
		if not force:
			if self.state == state and self.ext == ext:
				return
		d = chr(self.code)
		if ext is not None:
			d += chr(switch_codes[state] | 0x20)
			d += chr(ext)
		else:
			d += chr(switch_codes[state])
		
		d = self.parent.send(d, handler=self.handler)
		def done(_):
			self.state = state
			self.ext = ext
			return _
		d.addCallback(done)
		return d

	def get(self, state, ext=None, handler=None):
		simple_event(Context(), "fs20","state", \
			state, ext if ext is not None else "-",
			*self.name)


	def getReply(self, ext=None, handler=None):
		raise NotImplementedError


class FS20switches(AttributedStatement):
	name = ("fs20","switch")
	doc = "FS20 controllers"
	long_doc="""\
fs20 switch ‹house_code› ‹name…›
  - Start declaring FS20 switches with that house code.
    To modify an existing list of switches, omit either the house_code
	or the name.
"""

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.actions = 0
		self.new_hc = None
		self.hc = None
		self.new_sw = []

	def start_block(self):
		event = self.params(self.ctx)
		if not len(event):
			raise SyntaxError(u"Usage: fs20 switch ‹name…›")

		try:
			self.hc = codenames[Name(event)]
		except KeyError:
			self.new_hc = True
		else:
			self.new_hc = False

	def run(self,ctx,**k):
		event = self.params(self.ctx)

		if self.new_hc is None:
			raise SyntaxError(u"‹fs20 switch› without sub-statements does nothing!")
		if self.code is None and self.hc is None:
			raise SyntaxError(u"A new ‹fs20 switch› needs a ‹code› sub-statement!")
		if self.code is not None:
			if self.hc is not None:
				self.hc.code = self.code ## update
			else:
				self.hc = SwitchGroup(self.code, Name(event))

		if self.new_hc:
			self.hc.add()
		for s in self.new_sw:
			if s.code in self.hc.devs:
				raise RuntimeError(u"The code ‹%d› is already known in ‹%d›" % (to_dev(s.code),to_hc(self.hc.code)))
			s.parent = self.hc
			s.add()

	def add_sw(self,s):
		self.new_sw.append(s)


class FS20code(Statement):
	name = ("code",)
	doc = "Set the house code for a new switch group"
	long_doc=u"""\
fs20 ‹name…›:
	code 12343212
  - Set the house code for a new switch group.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u"Usage: code ‹code›")
		self.parent.code = from_hc(event[0])
FS20switches.register_statement(FS20code)


class FS20addswitch(AttributedStatement):
	name = ("add",)
	doc = "Add a new named switch"
	long_doc=u"""\
add ‹code› ‹name…›
  - Add a new named FS20 switch. By default, it can do "on" and "off".
"""
	immediate = True

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.code = None
		
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u"Usage: add ‹code› ‹name…›")
		code = from_dev(event[0])
		name = Name(event[1:])

		self.parent.add_sw(Switch(code, name))
FS20switches.register_statement(FS20addswitch)


class FS20delswitch(AttributedStatement):
	name = ("del",)
	doc = "Delete a switch (by name or code)"
	long_doc=u"""\
del ‹code› | ‹name…›
  - Delete a named FS20 switch. You can use the device code or its name.
"""

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.code = None
		
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: del ‹code› | ‹name…›")
		name = Name(event)
		try:
			d = devnames[name]
		except KeyError:
			if len(name) > 1: raise
			d = from_dev(name[0])
			d = self.parent.hc.devs[d]
		else:
			if d.parent != self.parent.hc:
				raise RuntimeError("The named device has houce code %d, not %d" % (to_hc(d.parent.code),to_hc(self.parent.hc.code)))

		d.delete()
FS20switches.register_statement(FS20delswitch)


class FS20send(AttributedStatement):
	name = ("send","fs20")
	doc = "Send a message to a FS20 device"
	long_doc=u"""\
send fs20 ‹msg› -|‹aux› ‹name…›
  - Send a message to this FS20 device.
    The ‹aux› value, if given, results in an extended message.
"""

	def __init__(self,*a,**k):
		super(AttributedStatement,self).__init__(*a,**k)
		self.code = None
		
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3:
			raise SyntaxError(u"Usage: send fs20 ‹msg› -|‹aux› ‹name…›")
		name = Name(event[2:])
		try:
			d = devnames[name]
		except KeyError:
			raise RuntimeError(u"Device ‹%s› not found" % (name,))

		if event[1] == "-":
			ext = None
		else:
			ext = int(event[1])
		d.set(event[0],ext)



class fs20switch(Module):
	"""\
		Basic fs20 switch control.
		"""

	info = "Basic fs20 switches"

	def load(self):
		main_words.register_statement(FS20switches)
		main_words.register_statement(FS20send)
	
	def unload(self):
		main_words.unregister_statement(FS20switches)
		main_words.unregister_statement(FS20send)
	
init = fs20switch

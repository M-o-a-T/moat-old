# -*- coding: utf-8 -*-

##
##  Copyright © 2012, Matthias Urlichs <matthias@urlichs.de>
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
This code holds common subcommands for specifying delays and related stuff.

"""

from __future__ import division,absolute_import

from homevent.statement import Statement
from homevent.times import time_delta,time_until,now

class DelayError(RuntimeError):
	def __init__(self,w):
		self.waiter = w
	def __str__(self):
		return self.text % (" ".join(str(x) for x in self.waiter.name),)
	def __unicode__(self):
		return self.text % (" ".join(unicode(x) for x in self.waiter.name),)

class DelayDone(DelayError):
	text = u"Delay ‹%s› is finished"

class DelayCancelled(DelayError):
	"""An error signalling that a wait was killed."""
	no_backtrace = True
	text = u"Waiter ‹%s› was cancelled"


class DelayFor(Statement):
	name = "for"
	doc = "specify the time to delay"
	long_doc=u"""\
for ‹timespec›
	- specify the absolute time to delay for.
	  N sec / min / hour / day / month / year
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: for ‹timespec…›')

		def delta():
			return time_delta(event, now=now(self.parent.force))
		self.parent.timespec = delta
	

class DelayUntil(Statement):
	name = "until"
	doc="delay until some timespec matches"
	long_doc=u"""\
until FOO…
	- delay processsing until FOO matches the current time.
	  Return immediately if it matches already.
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: until ‹timespec…›')
		def delta():
			return time_until(event, now=now(self.parent.force))
		self.parent.timespec = delta
					

class DelayWhile(Statement):
	name = "while"
	doc="delay while some timespec matches"
	long_doc=u"""\
while FOO…
	- delay processsing while FOO matches the current time
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: while ‹timespec…›')
		def delta():
			return time_until(event, invert=True, now=now(self.parent.force))
		self.parent.timespec = delta
					

class DelayNext(Statement):
	name = "next"
	doc="delay until some timespec does not match and then matches again"
	long_doc=u"""\
next FOO...
	- delay processsing until the next time FOO matches
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: until next ‹timespec…›')

		def delta():
			s = time_until(event, invert=True, now=now(self.parent.force))
			return time_until(event, now=s)
		self.parent.timespec = delta
					


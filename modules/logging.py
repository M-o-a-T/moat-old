# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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
This code does basic configurable logging.

log DEBUG "foo bar baz"
	- sends to the log
log WARN
	- logs warning (and other) messages
log
	- reports logging levels

"""

from homevent.module import Module
from homevent.statement import Statement, main_words
from homevent import logging
from homevent.logging import log, Logger, register_logger,unregister_logger,\
	LogNames

import sys

class OutLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def _log(self,level,txt):
		if txt == ".":
			print >>self.out,txt
		else:
			print >>self.out,LogNames[level]+"> "+txt

	def flush(self):
		if hasattr(self.out,"flush"):
			self.out.flush()

	def end_logging(self):
		super(OutLogger,self).end_logging()
		del self.out.logger


class LogHandler(Statement):
	name=("log",)
	doc="configure reporting"
	long_doc="""\
log DEBUG "foo bar baz"
	- sends to the log
log WARN
	- logs warning (and other) messages
log
	- reports available logging levels
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		try:
			out = self.ctx.out
		except KeyError:
			out = sys.stderr
		if not len(event):
			for s,v in LogNames.iteritems():
				print >>out,"%d = %s" % (s,v)
			print >>out,"."
			return None
		if len(event) > 1:
			log(getattr(logging,event[0].upper()), *event[1:])
		else:
			level = getattr(logging,event[0].upper())
			if level == logging.NONE:
				if hasattr(out,"logger"):
					unregister_logger(out.logger)
					del out.logger
			else:
				if hasattr(out,"logger"):
					out.logger.level = level
				else:
					try: out = self.ctx.out
					except KeyError: out = sys.stderr
					logger = OutLogger(out=out, level=level)
					register_logger(logger)
					try: out.logger = logger
					except AttributeError: pass # file objects don't


class LoggingModule(Module):
	"""\
		This is a module to control logging stuff to the current channel.
		"""

	info = "control logging"

	def load(self):
		main_words.register_statement(LogHandler)
	
	def unload(self):
		main_words.unregister_statement(LogHandler)
	
init = LoggingModule

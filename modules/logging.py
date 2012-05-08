# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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
from homevent.logging import log, Logger, LogNames, log_level, Loggers
from homevent.check import register_condition,unregister_condition

import sys

class OutLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def _log(self,level,*txt):
		if len(txt) == 1 and txt[0] == ".":
			print >>self.out,txt[0]
		else:
			super(OutLogger,self)._log(level,*txt)

	def _slog(self,level,txt):
		print >>self.out,LogNames[level]+">",txt

	def _flush(self):
		if hasattr(self.out,"flush"):
			self.out.flush()

	def end_logging(self):
		super(OutLogger,self).end_logging()
		del self.out.logger


class LogHandler(Statement):
	name="log"
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
		except AttributeError:
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
					out.logger.delete()
					del out.logger
			else:
				if hasattr(out,"logger"):
					out.logger.level = level
				else:
					try: out = self.ctx.out
					except AttributeError: out = sys.stderr
					logger = OutLogger(out=out, level=level)
					try: out.logger = logger
					except AttributeError: pass # file objects don't
					except:
						logger.delete()
						raise


class LogLevelHandler(Statement):
	name="log limit"
	doc="limit logging level"
	long_doc="""\
log limit event DEBUG
	- limit this kind of event to the given level;
      messages that are more detailed than that will be suppressed.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1 or len(event) > 2:
			SyntaxError(u"Usage: log limit ‹type› ‹level›")
		name = event[0]
		if len(event) == 2:
			level = getattr(logging,event[1].upper())
			log_level(name,level)
		else:
			try:
				out = self.ctx.out
			except AttributeError:
				out = sys.stderr
			print >>out, LogNames(log_level(name))


class LoggingModule(Module):
	"""\
		This is a module to control logging stuff to the current channel.
		"""

	info = "control logging"

	def load(self):
		main_words.register_statement(LogHandler)
		main_words.register_statement(LogLevelHandler)
		register_condition(Loggers.exists)
	
	def unload(self):
		main_words.unregister_statement(LogHandler)
		main_words.unregister_statement(LogLevelHandler)
		unregister_condition(Loggers.exists)
	
init = LoggingModule

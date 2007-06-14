#!/usr/bin/python
# -*- coding: utf-8 -*-

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
from homevent.logging import TRACE,DEBUG,INFO,WARN,ERROR,PANIC,NONE
from homevent.logging import log, Logger, register_logger,unregister_logger,
	LogNames


class OutLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def _log(self,level,txt):
		if txt == ".":
			print >>self.out,txt
		else:
			print >>self.out,LogNames[level]+"> "+txt

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
		out = self.ctx.out
		if not len(event):
			for s,v in LogNames.iteritems():
				print >>out,"%d = %s" % (s,v)
			print >>out,"."
			return None
		if len(event) > 1:
			log(globals()[event[0]], *event[1:])
		else:
			level = globals()[event[0]]
			if level == NONE:
				if hasattr(out,"logger"):
					unregister_logger(out.logger)
					del out.logger
			else:
				if hasattr(out,"logger"):
					out.logger.level = level
				else:
					out.logger = OutLogger(out=self.ctx.out, level=level)
					register_logger(out.logger)


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

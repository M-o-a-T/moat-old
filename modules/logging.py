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
from homevent.statement import SimpleStatement
from homevent.interpreter import main_words
from homevent.logging import TRACE,DEBUG,INFO,WARN,ERROR,PANIC
from homevent.logging import log, Logger, register_logger,unregister_logger

NONE=9

LogName={
	TRACE:"TRACE",
	DEBUG:"DEBUG",
	WARN:"WARN",
	INFO:"INFO",
	ERROR:"ERROR",
	PANIC:"PANIC",
}
class OutLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def _log(self,level,txt):
		if txt == ".":
			print >>self.out,txt
		else:
			print >>self.out,LogName[level]+"> "+txt

	def end_logging(self):
		super(OutLogger,self).end_logging()
		del self.out.logger


class LogHandler(SimpleStatement):
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
		w = event[len(self.name):]
		out = self.ctx.out
		if not len(w):
			for s,v in LogName.iteritems():
				print >>out,"%d = %s" % (s,v)
			print >>out,"."
			return None
		if len(w) > 1:
			log(globals()[w[0]], *w[1:])
		else:
			level = globals()[w[0]]
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

	def __init__(self, name, *args):
		super(LoggingModule,self).__init__(name,*args)
	
	def load(self):
		main_words.register_statement(LogHandler)
	
	def unload(self):
		main_words.unregister_statement(LogHandler)
	
init = LoggingModule

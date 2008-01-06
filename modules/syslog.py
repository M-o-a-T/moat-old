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
	TRACE,DEBUG,INFO,WARN,ERROR,PANIC

import sys
import syslog
import socket
import errno

facilities = {
	"kern": syslog.LOG_KERN,
	"user": syslog.LOG_USER,
	"mail": syslog.LOG_MAIL,
	"daemon": syslog.LOG_DAEMON,
	"auth": syslog.LOG_AUTH,
	"lpr": syslog.LOG_LPR,
	"news": syslog.LOG_NEWS,
	"uucp": syslog.LOG_UUCP,
	"cron": syslog.LOG_CRON,
	"local0": syslog.LOG_LOCAL0,
	"local1": syslog.LOG_LOCAL1,
	"local2": syslog.LOG_LOCAL2,
	"local3": syslog.LOG_LOCAL3,
	"local4": syslog.LOG_LOCAL4,
	"local5": syslog.LOG_LOCAL5,
	"local6": syslog.LOG_LOCAL6,
	"local7": syslog.LOG_LOCAL7,
}
levels = {
	"emerg": syslog.LOG_EMERG,
	"panic": syslog.LOG_EMERG,
	"alert": syslog.LOG_ALERT,
	"crit": syslog.LOG_CRIT,
	"err": syslog.LOG_ERR,
	"error": syslog.LOG_ERR,
	"warning": syslog.LOG_WARNING,
	"warn": syslog.LOG_WARNING,
	"notice": syslog.LOG_NOTICE,
	"info": syslog.LOG_INFO,
	"debug": syslog.LOG_DEBUG,
}
local_levels = {
	TRACE: syslog.LOG_DEBUG,
	DEBUG: syslog.LOG_NOTICE,
	INFO: syslog.LOG_INFO,
	WARN: syslog.LOG_WARNING,
	ERROR: syslog.LOG_ERR,
	PANIC: syslog.LOG_EMERG,
}

class SysLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def __init__(self, address="/dev/log", facility="user", level="info"):
		self.address = address
		self.facility_name = facility
		self.level_name = level
		self.facility = facilities[facility]
		self.level = getattr(logging,level.upper())

		if isinstance (address,tuple):
			self.socket = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
		else:
			self.socket = socket.socket (socket.AF_UNIX, socket.SOCK_DGRAM)
		self.socket.connect (address)

	def _log(self,level,txt):
		if isinstance(txt,unicode):
			txt = txt.encode("utf-8")

		while True:
			try:
				self.socket.send("<%d>HomEvenT: %s\0" % (self.facility | local_levels[level],txt))
			except socket.error,err:
				if err.args[0] != errno.EINTR:
					raise
			else:
				break

	def flush(self):
		pass

loggers = {}

def gen_addr(a="/dev/log",b=None):
	"""Return an address from one or two arguments"""
	if a.startswith("/"):
		assert b == None
		return a
	if b is None:
		b = 514
	else:
		b = int(b)
	return (a,b)

class SyslogHandler(Statement):
	name=("syslog",)
	doc="configure reporting to syslog"
	long_doc=u"""\
syslog ‹facility› ‹level› [‹destination›]
	- sets up logging to syslog.
      ‹facility› is standard syslog ("user", "local4"…; default to "user").
      ‹level› is one of HomEvenT's logging levels as reported by "log".
      ‹destination› can be either a Unix socket (needs to start with a /)
                    or a host name, optionally followed by a port number.
                    Default is the local syslog daemon.
      There cannot be more than one log per facility and destination.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2 or len(event) > 4:
			raise SyntaxError(u"Usage: syslog ‹facility› ‹level› [‹destination›]")
		dest = gen_addr(*event[2:])

		facility = event[0]
		logger = SysLogger(address=dest, facility=facility, level=event[1])

		name = (facility, dest)
		try:
			old_logger = loggers.pop(name)
		except KeyError:
			pass
		else:
			unregister_logger(old_logger)
		register_logger(logger)
		loggers[name] = logger

class NoSyslogHandler(Statement):
	name=("del","syslog")
	doc="remove reporting to syslog"
	long_doc=u"""\
del syslog ‹facility› [‹destination›]
	- removes a syslogger.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1 or len(event) > 3:
			raise SyntaxError(u"Usage: no syslog ‹facility› [‹destination›]")
		dest = gen_addr(*event[1:])

		facility = event[0]
		name = (facility, dest)
		unregister_logger(loggers.pop(name))


class SyslogLister(Statement):
	name=("list","syslog")
	doc="list syslog reporters"
	long_doc=u"""\
list syslog [‹facility› [‹destination›]]
	- Show loggers. If you add the destination, list additional details.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 3:
			raise SyntaxError(u"Usage: no syslog ‹facility› [‹destination›]")
		elif not len(event):
			for name,logger in loggers.iteritems():
				print >>ctx.out,logger.facility_name,logger.level_name," ".join(unicode(x) for x in name)
		else:
			dest = gen_addr(*event[1:])
			facility = event[0]
			name = (facility, dest)
			logger = loggers[name]
			print >>ctx.out,"Facility:", logger.facility
			print >>ctx.out,"Address:", logger.address
			print >>ctx.out,"Level:", logger.level
		print >>ctx.out,"."



class SyslogModule(Module):
	"""\
		Log to syslog.
		"""

	info = "control logging to syslog"

	def load(self):
		main_words.register_statement(SyslogHandler)
		main_words.register_statement(SyslogLister)
		main_words.register_statement(NoSyslogHandler)
	
	def unload(self):
		main_words.unregister_statement(SyslogHandler)
		main_words.unregister_statement(Sysloglister)
		main_words.unregister_statement(NoSyslogHandler)
	
init = SyslogModule

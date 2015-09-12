# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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
This code does basic configurable logging.

log DEBUG "foo bar baz"
	- sends to the log
log WARN
	- logs warning (and other) messages
log
	- reports logging levels

"""

import six

from moat import TESTING
from moat.module import Module
from moat.statement import Statement, main_words
from moat import logging
from moat.logging import log, BaseLogger, LogLevels, \
	TRACE,DEBUG,INFO,WARN,ERROR,PANIC
from moat.twist import fix_exception

import syslog
import socket
import errno
import os

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

class SysLogger(BaseLogger):
	"""\
		This class implements a logger that writes to syslog.
		"""
	def __init__(self, name, address="/dev/log", facility="user", level="info"):
		self.name = name
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
		super(SysLogger, self).__init__(self.level)

	def list(self):
		yield super(SysLogger,self)
		yield("facility", self.facility)
		yield("facility_name", self.facility_name)
		yield("address", self.address)
		yield("level", self.level)
		yield("level_name", self.level_name)
		
	def info(self):
		return "%s %s" % (self.facility_name,self.level_name)

	def _slog(self,level,txt):
		while True:
			try:
				self.socket.send((u"<%d>MoaT: %s%s" % (
				                  self.facility | local_levels[LogLevels[level]],
								  txt,
				                  "\0" if not TESTING else "\n")).encode('utf-8'))
			except socket.error as err:
				fix_exception(err)
				if err.args[0] != errno.EINTR:
					raise
			else:
				break

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
	name="syslog"
	doc="configure reporting to syslog"
	long_doc=u"""\
syslog ‹facility› ‹level› [‹destination›]
	- sets up logging to syslog.
      ‹facility› is standard syslog ("user", "local4"…; default to "user").
      ‹level› is one of MoaT's logging levels as reported by "log".
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

		if isinstance(dest,tuple):
			name = (facility,) + dest
		else:
			name = (facility,dest)
		SysLogger(name=name, address=dest, facility=facility, level=event[1])

class SyslogModule(Module):
	"""\
		Log to syslog.
		"""

	info = "control logging to syslog"

	def load(self):
		main_words.register_statement(SyslogHandler)
	
	def unload(self):
		main_words.unregister_statement(SyslogHandler)
	
init = SyslogModule

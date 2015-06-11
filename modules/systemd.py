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
This code runs arbitrary Python code.

exec some.module.foo bar baz
	- imports some.module and runs foo(bar,baz).
"""

import six
import gevent
import systemd.daemon as sd

from moat.statement import Statement, AttributedStatement, main_words
from moat.event import Event
from moat.run import process_failure, simple_event
from moat.context import Context
from moat.base import SName, Name
from moat import logging
from moat.twist import Jobber,fix_exception
from moat.module import Module
from moat.logging import log,DEBUG
from moat.interpreter import Interpreter
from moat.event_hook import OnEventBase

from dabroker.util import import_string

class KeepaliveHandler(Statement):
	name="keepalive"
	doc="tell systemd we're alive"
	long_doc="""\
keepalive
	- sends "WATCHDOG=1" to systemd
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError("No parameters here")

		sd.notify("WATCHDOG=1")

class ReadyHandler(Statement):
	name="send ready"
	doc="tell systemd we're live"
	long_doc="""\
send ready
	- sends "READY=1" to systemd
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError("No parameters here")

		sd.notify("READY=1")

class SendStatusHandler(Statement):
	name="send status"
	doc="tell systemd what's going on"
	long_doc="""\
send status foo bar
	- sends "STATUS=foo bar" to systemd
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError("No parameters make no sense")

		sd.notify("STATUS="+' '.join(event))

class SystemdModule(Module):
	"""\
		Talks to systemd
		"""

	info = "call out to Python"

	def load(self):
		main_words.register_statement(SendStatusHandler)
		main_words.register_statement(KeepaliveHandler)
		main_words.register_statement(ReadyHandler)
	
	def unload(self):
		main_words.unregister_statement(SendStatusHandler)
		main_words.unregister_statement(KeepaliveHandler)
		main_words.unregister_statement(ReadyHandler)

init = SystemdModule

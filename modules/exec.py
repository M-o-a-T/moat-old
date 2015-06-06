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
from moat.statement import Statement, AttributedStatement, main_words
from moat.event import Event
from moat.run import process_failure, simple_event
from moat.context import Context
from moat.base import SName, Name
from moat import logging
from moat.twist import fix_exception
from moat.module import Module
from moat.logging import log,DEBUG
from moat.interpreter import Interpreter
from moat.event_hook import OnEventBase

from dabroker.util import import_string

class OnEventExec(OnEventBase):
	def __init__(self,parent,args,name,fn):
		super(OnEventExec,self).__init__(parent, args, name=name)
		self.fn = fn

	def process(self, event,**k):
		super(OnEventExec,self).process(**k)
		try:
			self.fn(event)
		except Exception as ex:
			fix_exception(ex)
			process_failure(ex)

class EnvRunner(object):
	def __init__(self,ctx, name=()):
		self.ctx = ctx
		self.name = name

	def __call__(self,*a,**kw):
		attrs = []
		keys = {}
		for k,v in kw.items():
			if k.startswith('_'):
				if isinstance(v,six.integer_types+six.string_types+(float,)):
					v = (v,)
				attrs.append((k[1:],)+tuple(v))
			else:
				keys[k]=v
		ctx = self.ctx(**keys)
		if len(a)==1:
			a = a[0].split(' ')
		if attrs:
			r = Interpreter(ctx).complex_statement(self.name+tuple(a))

			for x in attrs:
				if len(x) == 2:
					x = (x[0],)+tuple(x[1].split(" "))
				r.simple_statement(x)
			r.done()
		else:
			Interpreter(ctx).simple_statement(self.name+tuple(a))
	
	def __getattr__(self,k):
		if k.startswith('_'):
			return super(EnvRunner,self).__getattr__(k)
		r = EnvRunner(self.ctx, self.name+(k,))
		setattr(self,k,r)
		return r

class Env(object):
	"""A wrapper class for hooking up Python code"""
	def __init__(self, parent, ctx):
		self.parent = parent
		self.ctx = ctx
		self.do = EnvRunner(ctx)
	
	def on(self, *args, **kw):
		doc=kw.pop('doc',None)
		name=kw.pop('name',None)
		if len(args) == 1:
			args = args[0].split('.')
		args = Name(*args)
		if name is None:
			name = SName(args)
		elif isinstance(name,six.string_types):
			name = SName(name.split(" "))

		def dec(fn):
			OnEventExec(self.parent, args, name, fn)
			return fn
		return dec

	def trigger(self, *a,**k):
		simple_event(self.ctx, *a,**k)

class ExecHandler(AttributedStatement):
	name="exec"
	doc="run Python code"
	long_doc="""\
exec some.module.FOO bar baz ...
	- Loads "some.module" and calls "foo(ENVIRONMENT, bar,baz,…) there.
	- env.ctx is the context
	- @env.on("foo.bar.baz", name=…,doc=…) is a decorator that runs the
	  decorated code when an event arrives. Sole argument is the event.
"""

	def __init__(self,*a,**k):
		self.vars = {}
		super(ExecHandler,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not event:
			raise SyntaxError("Events need at least one parameter")

		for k,v in self.vars.items():
			if k[0] == '$':
				k = ctx[k[1:]]
			try:
				if v[0] == '$':
					v = ctx[v[1:]]
			except TypeError: # not an int
				pass
			if k is not None and v is not None:
				setattr(event.ctx, k,v)

		proc = import_string(event[0])
		proc(Env(self,ctx), *event[1:])

@ExecHandler.register_statement
class ExecParam(Statement):
	name = "param"
	doc = "set a parameter"
	long_doc=u"""\
param ‹key› ‹val›
	The value ‹val› is attached to the event as ‹key›.

	The event handler will then be able to refer to ‹val› by ‹$key›.
"""
	def run(self,ctx,**k):
		event = self.par(ctx)
		if len(event) != 2:
			raise SyntaxError(u'Usage: param ‹key› ‹val›')
		self.parent.vars[event[0]] = event[1]

from moat.module import Module

class Path(Statement):
	name="path"
	doc="set python module path"
	long_doc = """\
path 'directory'
	adds the given directory to the list of paths where
	Python (not MoaT) modules are searched at.
	The directory probably needs to be quoted.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: path 'filename'")
		import sys
		sys.path.append(event[0])

class ExecModule(Module):
	"""\
		Contains a function to run arbitrary Python code.
		"""

	info = "call out to Python"

	def load(self):
		main_words.register_statement(ExecHandler)
		main_words.register_statement(Path)
	
	def unload(self):
		main_words.unregister_statement(ExecHandler)
		main_words.unregister_statement(Path)

init = ExecModule

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
We need code for conditionals.

test foo bar:
	true if state on what ever
	false

if test foo bar:
	do-something
else:
	do-something-else

on what ever:
	if test foo bar

This code implements the basic framework for checking conditions.
"""

from moat.statement import Statement,ComplexStatement, global_words

class Check(Statement):
	"""Abstrace base class for condition checks"""
	immediate = True
	def run(self,*a,**k):
		raise SyntaxError(u"‹%s› is not a statement you can execute.", " ".join(self.name))

	def check(self,*args):
		raise NotImplementedError("You need to override check().")

class Conditions(ComplexStatement):
	name = "conditions"
	doc = "List of conditions you can use in 'if' statements."
	long_doc = """\
help conditions : list the things you can test for.

'conditions' is not an executable statement.
"""
	immediate = True
	def run(self,*a,**k):
		raise SyntaxError(u"‹conditions› is not a statement you can execute.")
	
	def check_condition(self,ctx,*args):
		"""Check if a condition is met"""
		fn =  self.lookup(args)
		args = args[len(fn.name):]
		return fn(ctx=ctx).check(*args)

check_condition = Conditions().check_condition
register_condition = Conditions.register_statement
unregister_condition = Conditions.unregister_statement
	
global_words.register_statement(Conditions)


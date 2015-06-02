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
This code implements primitive "if true" and "if false" checks.

"""

from moat.check import Check,register_condition,unregister_condition
from moat.module import Module

class TrueCheck(Check):
	name="true"
	doc="always true."
	def check(self,*args):
		assert not args,"Truth doesn't have arguments"
		return True

class FalseCheck(Check):
	name="false"
	doc="always false."
	def check(self,*args):
		assert not args,"Falsehood doesn't have arguments"
		return False

class NoneCheck(Check):
	name="null"
	doc="check if the argument has a value."
	def check(self,*args):
		assert len(args)==1,u"The ‹null› check requires one argument"
		return args[0] is None

class EqualCheck(Check):
	name="equal"
	doc="check if the arguments are the same."
	def check(self,*args):
		assert len(args)==2,u"The ‹equal› check requires two arguments"
		a,b = args
		if a is None: return b is None
		try:
			return float(a) == float(b)
		except (ValueError,TypeError):
			return str(a) == str(b)

class LessCheck(Check):
	name="less"
	doc="check if the first argument is smaller."
	def check(self,*args):
		assert len(args)==2,u"The ‹less› check requires two arguments"
		a,b = args
		if a is None or b is None: return False
		try:
			return float(a) < float(b)
		except (ValueError,TypeError):
			return str(a) < str(b)

class GreaterCheck(Check):
	name="greater"
	doc="check if the first argument is larger."
	def check(self,*args):
		assert len(args)==2,u"The ‹greater› check requires two arguments"
		a,b = args
		if a is None or b is None: return False
		try:
			return float(a) > float(b)
		except (ValueError,TypeError):
			return str(a) > str(b)

class BoolModule(Module):
	"""\
		This module implements basic boolean conditions
		"""

	info = u"Boolean conditions. There can be only … two."

	def load(self):
		register_condition(TrueCheck)
		register_condition(FalseCheck)
		register_condition(NoneCheck)
		register_condition(EqualCheck)
		register_condition(LessCheck)
		register_condition(GreaterCheck)
	
	def unload(self):
		unregister_condition(TrueCheck)
		unregister_condition(FalseCheck)
		unregister_condition(NoneCheck)
		unregister_condition(EqualCheck)
		unregister_condition(LessCheck)
		unregister_condition(GreaterCheck)
	
init = BoolModule

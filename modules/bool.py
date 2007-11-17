# -*- coding: utf-8 -*-

"""\
This code implements primitive "if true" and "if false" checks.

"""

from homevent.check import Check,register_condition,unregister_condition
from homevent.module import Module

class TrueCheck(Check):
	name=("true",)
	doc="always true."
	def check(self,*args):
		assert not args,"Truth doesn't have arguments"
		return True

class FalseCheck(Check):
	name=("false",)
	doc="always false."
	def check(self,*args):
		assert not args,"Falsehood doesn't have arguments"
		return False

class NoneCheck(Check):
	name=("null",)
	doc="check if the argument has a value."
	def check(self,*args):
		assert len(args)==1,u"The ‹null› check requires one argument"
		return args[0] is None

class EqualCheck(Check):
	name=("equal",)
	doc="check if the arguments are the same."
	def check(self,*args):
		assert len(args)==2,u"The ‹equal› check requires two arguments"
		a,b = args
		if a is None: return b is None
		try:
			return float(a) == float(b)
		except ValueError:
			return str(a) == str(b)

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
	
	def unload(self):
		unregister_condition(TrueCheck)
		unregister_condition(FalseCheck)
		unregister_condition(NoneCheck)
		unregister_condition(EqualCheck)
	
init = BoolModule

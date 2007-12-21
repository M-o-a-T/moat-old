# -*- coding: utf-8 -*-

"""\
This code implements logging to RRD.

"""

from homevent.check import Check,register_condition,unregister_condition
from homevent.module import Module
from homevent.statement import Statement, main_words
from homevent.times import now
from homevent.base import Name

import os
import rrdtool

rrds = {} # name => path

class ExistsRRDCheck(Check):
	name=("exists","rrd")
	doc="Check if the RRD has been created"
	def check(self,*args):
		assert len(args), "Need exactly one argument (RRD name)"
		return Name(args) in rrds


class RRDHandler(Statement):
	name=("rrd",)
	doc="Creates an RRD object"
	long_doc=u"""\
rrd path dataset NAME
	Create a named RRD object.
	: NAME is a mnemonic name for this RRD.
	PATH is the file name. You probably need to quote it.
	DATASET is the dataset name in the RRD.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3:
			raise SyntaxError(u'Usage: rrd "/path/to/the.rrd" ‹varname› ‹name…›')
		fn = event[0]
		assert os.path.exists(fn), "the RRD file does not exist: ‹%s›" % (fn,)
		rrds[Name(event[2:])] = (fn, event[1])


class DelRRDHandler(Statement):
	name=("del","rrd")
	doc="Deletes an RRD object"
	long_doc=u"""\
del rrd NAME
	: Remove the named RRD object from the system.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: del rrd ‹name…›')
		del rrds[Name(event)]


class VarRRDHandler(Statement):
	name=("var","rrd")
	doc="assign a variable to some RRD state"
	long_doc=u"""\
var rrd variable item NAME
	: Assigns the named RRD dataset variable to a variable.
	"rrdtool info" prints this in ds[‹variable›] lines:
	ds[‹dataset›].‹item› = ‹value-of-item›

"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3:
			raise SyntaxError(u'Usage: var rrd ‹variable› ‹item› ‹name…›')
		fn,var = rrds[Name(event[2:])]
		setattr(self.parent.ctx,event[0],rrdtool.info(fn)["ds"][var][event[1]])


class RRDset(Statement):
	name=("set","rrd")
	doc="write a variable to a RRD file"
	long_doc=u"""\
set rrd value ‹name…›
	: Assigns the named RRD dataset variable to a variable.
	"rrdtool info" prints this in ds[‹variable›] lines:
	ds[‹dataset›].‹item› = ‹value-of-item›

"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u'Usage: set rrd ‹value› ‹name…›')
		fn,var = rrds[Name(event[1:])]
		# Using "N:" may run into a RRD bug
		# if we're really close to the next minute
		rrdtool.update(fn, "-t",var.encode("utf-8"), now().strftime("%s")+":"+unicode(event[0]).encode("utf-8"))


class RRDList(Statement):
	name=("list","rrd")
	doc="list of RRD files"
	long_doc="""\
list rrd
	shows a list of known RRD files.
list rrd ‹name…›
	shows details for that RRD.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for k,v in rrds.iteritems():
				v1,v2 = v
				print >>self.ctx.out, "%s : %s %s" % (" ".join(k),v1,v2)
			print >>self.ctx.out, "."
		else:
			n = Name(event)
			p,d = rrds[n]
			print  >>self.ctx.out, "Name:",n
			print  >>self.ctx.out, "File:",p
			print  >>self.ctx.out, "Dataset:",d
			for k,v in rrdtool.info(p)["ds"][d].iteritems():
				print  >>self.ctx.out, k+":",v


class RRDModule(Module):
	"""\
		This module provides tools for working with RRDs.
		"""

	info = "Words for RRD access"

	def load(self):
		register_condition(ExistsRRDCheck)
		main_words.register_statement(RRDHandler)
		main_words.register_statement(RRDset)
		main_words.register_statement(RRDList)
		main_words.register_statement(DelRRDHandler)
		main_words.register_statement(VarRRDHandler)
	
	def unload(self):
		unregister_condition(ExistsRRDCheck)
		main_words.unregister_statement(RRDHandler)
		main_words.unregister_statement(RRDset)
		main_words.unregister_statement(RRDList)
		main_words.unregister_statement(DelRRDtHandler)
		main_words.unregister_statement(VarRRDtHandler)
	
init = RRDModule

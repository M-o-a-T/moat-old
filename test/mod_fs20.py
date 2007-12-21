#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from twisted.internet import defer
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from homevent.fs20 import handler, register_handler
import homevent.fs20 as fs20
from homevent.logging import log,DEBUG
from test import run

#class dumper(handler):
#	def send(self,data):
#		log(DEBUG,"fs20 *send*", "".join(("%02x" % ord(x) for x in data)))
#		return defer.succeed(None)
#d = dumper()
#register_handler(d)
#assert fs20.default_handler == d, "default handler is wrong:"+repr(fs20.default_handler)+"/"+repr(d)

input = """\
if not exists module bool: load bool
if not exists module ifelse: load ifelse
if not exists module logging: load logging
if not exists module block: load block
if not exists module trigger: load trigger
if not exists module wait: load wait
if not exists module fs20tr: load fs20tr
if not exists module fs20switch: load fs20switch
if not exists module on_event: load on_event
if not exists module errors: load errors
#
fs20 switch 31413142 foo bar:
	add 1214 baz quux

block:
	if exists file "fs20_emit":
		fs20 receiver foobar:
			cmd "./fs20_emit"
		fs20 sender bar foo:
			cmd "./fs20_send"
	else:
		fs20 receiver foobar:
			cmd "test/fs20_emit"
		fs20 sender bar foo:
			cmd "test/fs20_send"
#
send fs20 on - baz quux
send fs20 off - baz quux
#
wait for 3
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")

run("fs20",input)


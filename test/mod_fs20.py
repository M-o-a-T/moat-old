#!/usr/bin/python
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

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module,Load
from moat.statement import main_words
from moat.check import register_condition
from moat.fs20 import handler, register_handler
import moat.fs20 as fs20
from moat.logging import log,DEBUG
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
if not exists module fs20switch: load fs20switch
if not exists module fs20em: load fs20em
if not exists module fs20en: load fs20en
if not exists module fs20tx: load fs20tx
if not exists module on_event: load on_event
#
list fs20 code
list fs20 switch

fs20 switch foo bar:
	code 31413142
	add baz quux:
		code 1214

list fs20 code
list fs20 code foo bar
list fs20 switch
list fs20 switch baz quux

fs20 en gas:
	code gas_meter 9
	delta

fs20 em inside:
	code thermo_hygro 1
	scale temperature * -1.2

fs20 em one:
	code thermo_hygro 3
fs20 em two:
	code thermo_hygro 3

fs20 tx tempix:
	code thermo 7
	scale temperature * +2.3

fs20 tx hygrix:
	code hygro 7
	scale humidity * -1.0

set fs20 em temperature 12 one
set fs20 em temperature 15 two

list fs20 em one
list fs20 em two

list fs20 en
list fs20 en gas

list fs20 tx tempix
list fs20 tx hygrix

#block:
#	if exists file "fs20_recv":
#		fs20 receiver foobar:
#			cmd "./fs20_recv"
#		fs20 sender bar foo:
#			cmd "./fs20_xmit"
#	else:
#		fs20 receiver foobar:
#			cmd "test/fs20_recv"
#		fs20 sender bar foo:
#			cmd "test/fs20_xmit"
#
wait:
	for 0.5
	debug force
#list fs20 receiver
#list fs20 receiver foobar
#list fs20 sender
#list fs20 sender bar foo
send fs20 on - baz quux
send fs20 off - baz quux
#
wait:
	for 3
	debug force
wait:
	for 0.1
	debug force
list fs20 em
list fs20 em one
list fs20 em two
list fs20 en
list fs20 en gas
list fs20 tx
list fs20 tx tempix
list fs20 tx hygrix
#async:
#	wait:
#		for 0.1
#		debug force
#	del fs20 receiver foobar
#	wait:
#		for 0.1
#		debug force
#	del fs20 sender bar foo
wait:
	for 0.7
	debug force
#list fs20 receiver
#list fs20 sender
shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("block")
load_module("file")
load_module("data")
load_module("ifelse")
load_module("path")

run("fs20",input)


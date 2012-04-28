#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from homevent.statement import DoNothingHandler,main_words
from homevent.check import register_condition
from test import run

input = """\
if not exists module bool: load bool
if not exists module ifelse: load ifelse
if not exists module logging: load logging
if not exists module block: load block
if not exists module trigger: load trigger
if not exists module wait: load wait
if not exists module onewire: load onewire
if not exists module on_event: load on_event
if not exists module errors: load errors
#
on onewire scanned A * * *:
	name scanned

	del on scanned
	var onewire X "000010EF0000" temperature
	trigger thermo $X
	del wait yawn

connect onewire A localhost 54300
#
block:
	try:
		wait yawn:
			for 10
			debug force
		shutdown
	catch:
		do nothing

log TRACE DirStart
dir onewire A
log TRACE DirDev
dir onewire "000010EF0000"
block:
	if exists onewire "000010EF0000":
		log TRACE yes
	else:
		log TRACE no
log TRACE DirStop
#set onewire 30 "000010EF0000" templow ## not when testing
scan onewire A
dir onewire A
disconnect onewire A
wait END:
	for 1
	debug force
shutdown
"""

main_words.register_statement(DoNothingHandler)
main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)
register_condition(ModuleExists)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")
load_module("data")

run("onewire",input)


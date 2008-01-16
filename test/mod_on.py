#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
from homevent.module import load_module
from homevent.statement import DoNothingHandler, main_words

from test import run

input = u"""\
on fuß:
	name Schau auf deine Füße
	do nothing
on num 1:
	name Txt2Num
	do nothing
on num "2":
	name Num2Txt
	do nothing
on num 3:
	name num2num
	do nothing
on foo:
	prio 49
	name Skipped One
	if false
	log ERROR "This should not be executed"
on foo:
	prio 50
	name Skipped Two
	if true:
		next handler
	log ERROR "This should also not be executed"
on foo:
	prio 55
	name Last Handler
	log DEBUG "This is logged once"
	doc "Causes the prio-60 thing to not be executed"
on foo:
	prio 60
	name not executed
	doc "Is not executed because of the former 'skip next' (until that's gone)"
	log DEBUG "This is logged once too"
on bar *:
	block:
		sync trigger $1
list on
list on Skipped One
list on Skipped Two
sync trigger bar foo
del on Last Handler
sync trigger bar foo
del on 1
list on
trigger fuß
trigger num "1"
trigger num 2
trigger num 3
shutdown
"""

main_words.register_statement(DoNothingHandler)
main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("trigger")
load_module("on_event")
load_module("ifelse")
load_module("bool")
load_module("data")
load_module("logging")

run("on",input)


#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
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
from moat.module import load_module
from moat.statement import DoNothingHandler, main_words

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
	name Skipped One
	if false
	log ERROR "This should not be executed"
on foo:
	name Skipped Two
	if true:
		exit handler
	log ERROR "This should also not be executed"
on foo:
	name Another Handler
	log DEBUG "This is logged once"
on bar *:
	block:
		trigger $1 :sync
on baz:
	block:
		log DEBUG got baz $quux
		if equal $quux "two":
			log TRACE Yes
			set state nix dud
		else:
			log ERROR no quux $quux
list on
list on Skipped One
list on Skipped Two
trigger bar foo :sync
del on Another Handler
trigger bar foo :sync
del on fuß
list on
trigger fuß
trigger baz:
	param quux one
block:
	state dud
	set state two dud
	var state vav dud
	log DEBUG vav is $vav
	trigger baz dud $vav
	trigger baz:
		param quux $vav
wait :for 0.1
block:
	var state va dud
	if equal $va "nix":
		log TRACE Yes
	else:
		log ERROR handler not called
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
load_module("state")
load_module("wait")

run("on",input)


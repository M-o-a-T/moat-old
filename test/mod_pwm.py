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
from homevent.statement import main_words
from test import run

input = """\
block:
	if exists pwm foo bar:
		log DEBUG No1
	else:
		log DEBUG Yes
pwm foo bar:
	type PWM
	interval 10

on pcm set *X foo bar:
	log DEBUG PCM is now $X
	wait: for 0.1

block:
	if exists pwm foo bar:
		log DEBUG Yes
	else:
		log DEBUG No2
list pwm
list pwm foo bar
set pwm 0.1 foo bar
wait: for 0.5
list pwm foo bar
wait: for 8.5
list pwm foo bar
wait: for 15
list pwm
shutdown now
"""

main_words.register_statement(ShutdownHandler)
load_module("ifelse")
load_module("data")
load_module("pwm")
load_module("logging")
load_module("block")
load_module("wait")
load_module("on_event")

run("pwm",input)


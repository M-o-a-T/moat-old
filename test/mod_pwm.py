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
from moat.module import load_module
from moat.statement import main_words
from test import run

input = """\
block:
	if exists pwm foo bar:
		log ERROR No1
	else:
		log TRACE Yes
pwm foo bar:
	type PWM
	interval 10

on pwm change foo bar:
	log DEBUG PWM is now $value
	wait: for 0.1

block:
	if exists pwm foo bar:
		log TRACE Yes
	else:
		log ERROR No2
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


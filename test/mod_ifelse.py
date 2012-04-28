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
from homevent.module import load_module
from homevent.statement import main_words
from test import run

input = """\
block:
	if true:
		log DEBUG Yes
	else:
		log DEBUG No1
	if true:
		log DEBUG Yes
	else if true:
		log DEBUG No2
	if true:
		log DEBUG Yes
	else if true:
		log DEBUG No3
	else:
		log DEBUG No4
	if true:
		log DEBUG Yes
	else if false:
		log DEBUG No5
	else:
		log DEBUG No6

block:
	if false:
		log DEBUG No7
	else:
		log DEBUG Yes
	if false:
		log DEBUG No8
	else if true:
		log DEBUG Yes
	if false:
		log DEBUG No9
	else if false:
		log DEBUG No10
	else:
		log DEBUG Yes

block:
	if equal 2 2.0:
		log DEBUG Yes
	else:
		log DEBUG No11
	if equal 1 2:
		log DEBUG No12
	else:
		log DEBUG Yes
	if equal 0 Foo:
		log DEBUG No13
	else:
		log DEBUG Yes
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("bool")
load_module("block")

run("ifelse",input)

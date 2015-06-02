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
#log TRACE
input fake :name foo bar
output fake:
	name foo bar
	range 1 9
	range 111 222
	value TEST GRMPF
	value one two three
list input
list input foo bar
list output
list output foo bar

set output TEST foo bar
block:
	var input bla foo bar
	if equal $bla "TEST":
		log TRACE Yes
	else:
		log ERROR No1 $bla

block:
	try:
		set output 0 foo bar
		log ERROR No 0
	catch:
		log TRACE Yes
	set output 1 foo bar
	set output 9 foo bar
	set output 123 foo bar
	try:
		set output 10 foo bar
		log ERROR No 10
	catch:
		log TRACE Yes
	set output one foo bar
	set output two foo bar
	set output three foo bar
	try:
		set output four foo bar
		log ERROR No four
	catch:
		log TRACE Yes

set output GRMPF foo bar
block:
	var input bla foo bar
	if equal $bla "TEST":
		log ERROR No $bla
	else:
		log TRACE Yes

list input foo bar
list output foo bar

shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("ifelse")
load_module("data")
load_module("block")
load_module("bool")
load_module("logging")
load_module("tests")
load_module("errors")

run("io",input)


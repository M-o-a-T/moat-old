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
from moat.statement import main_words
from test import run

input = """\
block:
	if true:
		log TRACE Yes
	else:
		log ERROR No1
	if true:
		log TRACE Yes
	else if true:
		log ERROR No2
	if true:
		log TRACE Yes
	else if true:
		log ERROR No3
	else:
		log ERROR No4
	if true:
		log TRACE Yes
	else if false:
		log ERROR No5
	else:
		log ERROR No6

block:
	if false:
		log ERROR No7
	else:
		log TRACE Yes
	if false:
		log ERROR No8
	else if true:
		log TRACE Yes
	if false:
		log ERROR No9
	else if false:
		log ERROR No10
	else:
		log TRACE Yes

block:
	if equal 2 2.0:
		log TRACE Yes
	else:
		log ERROR No11
	if equal 1 2:
		log ERROR No12
	else:
		log TRACE Yes
	if equal 0 Foo:
		log ERROR No13
	else:
		log TRACE Yes
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("bool")
load_module("block")

run("ifelse",input)

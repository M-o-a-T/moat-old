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

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module
from moat.statement import main_words
from test import run

input = """\
block:
	if exists path "..":
		log TRACE Yes
	else:
		log ERROR No1
	if exists path "...":
		log ERROR No2
	else:
		log TRACE Yes
	if exists directory "..":
		log TRACE Yes
	else:
		log ERROR No3
	if exists directory "README":
		log ERROR No4
	else:
		log TRACE Yes
	if exists file "README":
		log TRACE Yes
	else:
		log ERROR No5
	if exists file "..":
		log ERROR No6
	else:
		log TRACE Yes
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("path")
load_module("block")

run("path",input)

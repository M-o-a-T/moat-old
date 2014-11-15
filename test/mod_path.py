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

from homevent import patch;patch()
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.statement import main_words
from test import run

input = """\
block:
	if exists path "..":
		log DEBUG Yes
	else:
		log DEBUG No1
	if exists path "...":
		log DEBUG No2
	else:
		log DEBUG Yes
	if exists directory "..":
		log DEBUG Yes
	else:
		log DEBUG No3
	if exists directory "README":
		log DEBUG No4
	else:
		log DEBUG Yes
	if exists file "README":
		log DEBUG Yes
	else:
		log DEBUG No5
	if exists file "..":
		log DEBUG No6
	else:
		log DEBUG Yes
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("path")
load_module("block")

run("path",input)

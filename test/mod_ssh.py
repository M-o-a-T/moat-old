#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load
from homevent.statement import global_words
from test import run

global_words.register_statement(Load)


input = """\
load ssh
block:
	if exists directory "keys":
		ssh directory "keys"
	else:
		ssh directory "../keys"

# TODO: run an external test ‽
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("path")
load_module("ifelse")

run("ssh",input)


#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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
from homevent.module import load_module
from test import run

input = """\
log limit parser NONE
log limit token NONE
log DEBUG
log TRACE "This is not logged"
log DEBUG "This is logged"
log WARN "This is logged too"
log
log PANIC
log WARN "This is not logged either"
log limit event TRACE
log TRACE
trigger Logged :sync
log limit event ERROR
trigger Not Logged :sync
"""

h.main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("trigger")

run("logging",input)

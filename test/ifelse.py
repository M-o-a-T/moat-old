#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
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

shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("bool")
load_module("block")

run("ifelse",input)

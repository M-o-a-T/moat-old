#!/usr/bin/python
# -*- coding: utf-8 -*-
##BP
##
##  Copyright © 2008-2012, Matthias Urlichs <matthias@urlichs.de>
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
from moat.reactor import shut_down, mainloop
from moat.statement import main_words
from test import run

input = """\
#log TRACE
list avg

### time mode
avg test time :mode time
list avg
list avg test time
wait: for 0.2

set avg 2 test time
list avg test time
wait: for 1
list avg test time
set avg 5 test time
list avg test time
wait: for 1
list avg test time
set avg 0 test time
list avg test time
block:
	if exists avg test time:
		log TRACE Yes
	else:
		log ERROR No0
block:
	var avg X test time
	if equal $X 3.5:
		log TRACE Yes
	else:
		log ERROR No1 $X

wait: for 2
block:
	var avg X test time
	if equal $X 1.75:
		log TRACE Yes
	else:
		log ERROR No2 $X
	var avg Y test time :use value
	var avg Z test time :use prev_value
	log DEBUG values now $Y prev $Z

del avg test time




avg test moving :mode moving 3
list avg
list avg test moving 
wait: for 0.2

set avg 2 test moving
list avg test moving
wait: for 1
list avg test moving
set avg 5 test moving
list avg test moving
wait: for 2
list avg test moving
set avg -1 test moving
list avg test moving
wait: for 4
list avg test moving
set avg 8 test moving
list avg test moving
wait: for 4
list avg test moving
set avg 14 test moving
list avg test moving
block:
	if exists avg test moving:
		log TRACE Yes
	else:
		log ERROR No0
block:
	var avg X test moving
	if equal $X 7:
		log TRACE Yes
	else:
		log ERROR No1 $X

wait: for 2
block:
	var avg X test moving
	if equal $X 7:
		log TRACE Yes
	else:
		log ERROR No2 $X
	var avg Y test moving :use value
	var avg Z test moving :use prev_value
	log DEBUG values now $Y prev $Z

del avg test moving





avg test decay :mode decay 0.1
list avg
list avg test decay
wait: for 0.2

set avg 2 test decay
list avg test decay
wait: for 1
list avg test decay
set avg 22 test decay
list avg test decay
wait: for 1
list avg test decay
set avg -1 test decay
list avg test decay
block:
	if exists avg test decay:
		log TRACE Yes
	else:
		log ERROR No0
block:
	var avg X test decay
	if equal $X 3.5:
		log TRACE Yes
	else:
		log ERROR No1 $X

wait: for 2
block:
	var avg X test decay
	if equal $X 3.5:
		log TRACE Yes
	else:
		log ERROR No2 $X
	var avg Y test decay :use value
	var avg Z test decay :use prev_value
	log DEBUG values now $Y prev $Z

del avg test decay




## this is 0.1/second
avg test decaytime :mode decaytime 0.1 1
list avg
list avg test decaytime
wait: for 0.2

set avg 10 test decaytime
list avg test decaytime
wait: for 1
list avg test decaytime
set avg 110 test decaytime
list avg test decaytime
wait: for 1
list avg test decaytime
set avg 1 test decaytime
list avg test decaytime
block:
	if exists avg test decaytime:
		log TRACE Yes
	else:
		log ERROR No0
block:
	var avg X test decaytime
	if equal $X 20:
		log TRACE Yes
	else:
		log ERROR No1 $X

wait: for 2
list avg test decaytime

block:
	var avg X test decaytime
	var avg Y test decaytime :use value
	var avg Z test decaytime :use prev_value
	log DEBUG values avg $X now $Y prev $Z

del avg test decaytime








block:
	if exists avg test:
		log ERROR No3
	else:
		log TRACE Yes
list avg
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("avg")
load_module("block")
load_module("data")
load_module("logging")
load_module("wait")
load_module("tests")
load_module("ifelse")
load_module("bool")
load_module("on_event")

run("avg",input)


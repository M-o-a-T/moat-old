#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
from homevent.module import load_module,Load,ModuleExists
from homevent.statement import DoNothingHandler
from test import run

input = """\
if not exists module bool: load bool
if not exists module logging: load logging
if not exists module block: load block
if not exists module trigger: load trigger
if not exists module wait: load wait
if not exists module on_event: load on_event
if not exists module wago: load wago
log DEBUG

async:
	connect wago localhost 59069:
		name test
		#ping 1

on foo baba:
	send wago test Dc
	send wago test DI
	send wago test Dr

wait :for 0.1
# TODO

input wago test 1 1:
	name foo bar
	bool why whynot

output wago test 2 1:
	name foo baz
	bool hey ho

#wago counter baz:
#	port 1 2
#
#
set output on foo baz
block:
	var input port foo bar
	log DEBUG in_1 $port
	if input whynot foo bar:
		log DEBUG Yes
	else:
		log DEBUG No3
	send wago test Ds
	var input port foo bar
	log DEBUG in_2 $port

	if input why foo bar:
		log DEBUG Yes
	else:
		log DEBUG No4
#
async:
	send wago test DS
	set output off foo baz:
		for 2
	log DEBUG released
	send wago test DS
block:
	wait timed set A:
		for 0.2
		debug force
	send wago test DC

	list outtimer

	wait timed set B:
		for 1
		debug force
	#send wago test "D-"
	var output port foo baz
	log DEBUG out_1 $port

	if output ho foo baz:
		log DEBUG Yes
	else:
		log DEBUG No5
	wait timed set C:
		for 1
		debug force

	var output port foo baz
	log DEBUG out_2 $port

	if output hey foo baz:
		log DEBUG Yes
	else:
		log DEBUG No6
#set output hey foo baz
wait:
	for 0.1
	debug force
set output ho foo baz
wait:
	for 0.5
	debug force
	
list
list wago conn
list wago conn test
list wago server
list wago server test
block:
	if exists wago test:
		log DEBUG Yes
	else:
		log DEBUG No1
	if connected wago test:
		log DEBUG Yes
	else:
		log DEBUG No2
	if exists wago test stupid:
		log DEBUG No3
	else:
		log DEBUG Yes

shutdown
"""

h.main_words.register_statement(DoNothingHandler)
h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")
load_module("data")

run("wago",input)


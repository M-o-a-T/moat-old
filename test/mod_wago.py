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
from moat.module import load_module,Load
from moat.statement import DoNothingHandler,main_words
from moat.check import register_condition
from test import run

input = """\
if not exists module bool: load bool
if not exists module logging: load logging
if not exists module block: load block
if not exists module trigger: load trigger
if not exists module wait: load wait
if not exists module on_event: load on_event
if not exists module wago: load wago
if not exists module monitor: load monitor
log DEBUG

async:
	connect wago localhost 59069:
		name test
		keepalive 0.5 0.7
		#ping 1

on wago connect test:
	send wago test Dc
	send wago test DI
	send wago test Dr

wait:
	for 0.1
	debug force
if not connected wago test:
	log WARN not connected
	shutdown
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
		log TRACE Yes
	else:
		log ERROR No3
	send wago test Ds
	var input port foo bar
	log DEBUG in_2 $port

	if input why foo bar:
		log TRACE Yes
	else:
		log ERROR No4
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
		log TRACE Yes
	else:
		log ERROR No5
	wait timed set C:
		for 1
		debug force

	var output port foo baz
	log DEBUG out_2 $port

	if output hey foo baz:
		log TRACE Yes
	else:
		log ERROR No6
#set output hey foo baz
wait:
	for 0.1
	debug force
set output ho foo baz
wait:
	for 0.5
	debug force
	
# now test some monitors
send wago test "Dc"
send wago test "d 0.01"

monitor wago test 1 1:
	name test count up
	mode count 1
	level up
monitor wago test 1 1:
	name test count down
	mode count 1
	level down
monitor wago test 1 1:
	name test count both
	mode count 1
	level both

monitor wago test 1 1:
	name test report up
	mode report
	level up
monitor wago test 1 1:
	name test report down
	mode report
	level down
monitor wago test 1 1:
	name test report both
	mode report
	level both

wait:
	for 0.1
	debug force
send wago test "Ds"
wait:
	for 0.1
	debug force
send wago test "Dc"
wait:
	for 0.1
	debug force
send wago test "Ds"
wait:
	for 1
	debug force

list monitor
list monitor test count up
list monitor test count down
list monitor test count both
list monitor test report up
list monitor test report down
list monitor test report both
block:
	var monitor MH test count up
	var monitor ML test count down
	var monitor MB test count both
	if not equal $ML 1:
		log ERROR No ML $ML
	else if not equal $MH 2:
		log ERROR No MH $MH
	else if not equal $MB 3:
		log ERROR No M3 $M3
	else:
		log TRACE YesM $ML $MH $MB

	var monitor RH test report up
	var monitor RL test report down
	var monitor RB test report both
	if not equal $RL 1:
		log ERROR No RL $RL
	else if not equal $RH 2:
		log ERROR No RH $RH
	else if not equal $RB 3:
		log ERROR No R3 $R3
	else:
		log TRACE YesR $RL $RH $RB

del monitor test count up
del monitor test count down
del monitor test count both
del monitor test report up
del monitor test report down
del monitor test report both

# give the things time to die
wait:
	for 0.1
	debug force

list wago conn
list wago conn test
list wago server
list wago server test

block:
	if exists wago server test:
		log TRACE Yes
	else:
		log ERROR No1
	if connected wago test:
		log TRACE Yes
	else:
		log ERROR No2
	if exists wago server test stupid:
		log ERROR No3
	else:
		log TRACE Yes
del wago server test

log DEBUG now we test a nonexistent port
block:
	connect wago localhost 52998:
		name test nonexist
		retry 0.2 0.5
		#ping 1

wait poll nonexist:
	for 1
	debug force
list wago server test nonexist
del wago server test nonexist

log DEBUG now we test a port that always EOFs
async:
	connect wago localhost 59067:
		name test closing
		retry 0.12 0.5
		#ping 1
	
wait poll closing:
	for 1
	debug force
list wago server test closing
del wago server test closing
	
log DEBUG now we test a port that does not answer
async:
	connect wago localhost 59068:
		name test no_answer
		retry 0.12 0.5
		#ping 1
	
wait poll no_answer:
	for 1
	debug force
list wago server test no_answer
del wago server test no_answer
	
wait poll end:
	for 2
shutdown
"""

main_words.register_statement(DoNothingHandler)
main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")
load_module("data")

run("wago",input)


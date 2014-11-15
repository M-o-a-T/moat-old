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
	try:
		log DEBUG Yes A

	try:
		log DEBUG Yes B
	catch:
		log DEBUG No 01
	
	try:
		log DEBUG Yes C
	catch:
		log DEBUG No 11
	catch:
		log DEBUG No 12
	
	try:
		log DEBUG Yes D
		trigger error Foo A
		log DEBUG No 21

	try:
		log DEBUG Yes E
		trigger error Foo B
		log DEBUG No 31
	catch:
		log DEBUG Yes F $2

	try:
		log DEBUG Yes G
		trigger error Foo C
		log DEBUG No 41
	catch:
		log DEBUG Yes H $2
	catch:
		log DEBUG No 42

	try:
		log DEBUG Yes I
		trigger error Foo D
		log DEBUG No 51
	catch:
		log DEBUG Yes J $2
		trigger error Foo E
		log DEBUG No 52

	try:
		log DEBUG Yes K
		trigger error Foo F
		log DEBUG No 61
	catch:
		log DEBUG Yes L $2
		trigger error Foo G
		log DEBUG No 62
	catch:
		log DEBUG Yes M $2

	try:
		log DEBUG $foobar
		log DEBUG No 71
	catch AttributeError:
		log DEBUG Yes N KEY
	catch:
		log DEBUG No 72

	try:
		trigger error Foo Bar
		log DEBUG No 81
	catch Foo:
		log DEBUG No 82
	catch Foo Bar Baz:
		log DEBUG No 83
	catch Foo Bar:
		log DEBUG Yes O
	catch:
		log DEBUG No 84
		
	try:
		trigger error Foo Bar
		log DEBUG No 91
	catch *a:
		log DEBUG No 92
	catch *a *b *c:
		log DEBUG No 93
	catch *a *b:
		log DEBUG Yes P $a $b
	catch:
		log DEBUG No 94
		
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("errors")
load_module("bool")
load_module("block")

run("errors",input)

#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2010, Matthias Urlichs <matthias@urlichs.de>
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
from homevent.context import Context
from modules.onewire import OWFSwindmon

res=[(2,0.5),(2.0,0.55),(2.16567,0.58863),(2.44226,0.60851),(2.86361,0.49702),(7.99997,0.99997),(8.05551,0.92410)]

def dump(c):
	a,q = res.pop(0)
	assert abs(a-c.avg)<0.001
	assert abs(q-c.qavg)<0.001

class par(object):
	def __init__(self):
		self.ctx = Context()
c = OWFSwindmon(par(),"wind")
c.decay=0.1
c._process_value(2)
dump(c)
c._process_value(2)
dump(c)
c._process_value(3)
dump(c)
c._process_value(4)
dump(c)
c._process_value(8)
dump(c)
for i in range(100):
	c._process_value(8)
dump(c)
for i in range(100):
	c._process_value(7)
	c._process_value(9)
dump(c)

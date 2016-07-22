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

from moat.context import Context
from modules.onewire import OWFSwindmon

res=[(2,0),(2.0,0.20),(2.5562,0.35317),(3.15135,0.46385),(4.56156,0.35936),(7.9999,0.9999),(8.11711,0.92410)]

def dump(c):
	a,q = res.pop(0)
	assert abs(a-c.avg)<0.001, (a,c.avg)
	assert abs(q-c.qavg)<0.001, (q,c.qavg)

class par(object):
	def __init__(self):
		self.ctx = Context()
c = OWFSwindmon(par(),"wind")
c.decay=0.2
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

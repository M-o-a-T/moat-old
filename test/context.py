#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2010, Matthias Urlichs <matthias@urlichs.de>
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

from homevent.context import Context,default_context

c = Context()
assert not c._store
assert not c
c.foo="bar"
assert c
assert c.foo=="bar"

d = c(bla="fasel")
assert d.bla=="fasel"
assert d.foo=="bar"
try:
	c.bla
except AttributeError:
	pass
else:
	assert False

def ger(): return "gerede"
def fup(): return "fuppsi"
e = default_context(d,laber=ger)
assert e.foo=="bar"
assert e.laber=="gerede"
assert "foo" in e
del c.foo
assert "foo" not in c
assert "foo" not in e
assert "fupps" not in e

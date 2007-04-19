#!/usr/bin/python
# -*- coding: utf-8 -*-

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
except KeyError:
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

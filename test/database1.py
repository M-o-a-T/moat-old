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

from moat.database import DbStore
from moat.base import Name
from moat.reactor import shut_down,mainloop

s = DbStore(Name("Foo","bar"))
def main():
	s.clear()
	s.set("one",4)
	s.set(("two","three"),(4,5,6))

	def getter(a,b):
		_ = s.get(a)
		assert _ == b, "Check CallBack %r %r %r" % (_,a,b)
	getter("one",4)
	getter(("two","three"),(4,5,6))
	s.set("one",2)
	getter("one",2)

	shut_down()

mainloop(main)


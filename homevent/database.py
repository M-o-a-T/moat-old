# -*- coding: utf-8 -*-

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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

"""\
This is the core of database access.
"""

from homevent.base import Name
from storm.twisted.store import DeferredStore

SafeNames = {
	"Name":Name,
}

from he_storage import DbTable,database

#Db = DeferredStore(self.database)

class DbStore(object):
	"""This object implements a simple Deferred-enabled storage"""
	def __init__(self,cat):
		self.store = DeferredStore(database)
		self.category = repr(cat)
	
	def start(self):
		return self.store.start()
	
	def get(self, key):
		d = self.store.find(DbTable,
			DbTable.category == self.category,
			DbTable.name == repr(key))

		def got1(r):
			return r.one()
		def got2(r):
			r = r.value
			r = eval(r,SafeNames,{})
			return r
		d.addCallback(got1)
		d.addCallback(got2)
		def cmt(_):
			e = self.store.commit()
			e.addCallback(lambda x: _)
			return e
		def rlb(_):
			e = self.store.rollback()
			e.addBoth(lambda x: _)
			return e
		d.addCallback(cmt)
		d.addErrback(rlb)
		return d

	def delete(self, key):
		d = self.store.find(DbTable,
			DbTable.category == self.category,
			DbTable.name == repr(key))
		def got1(r):
			return r.one()
		def got2(r):
			return self.store.remove(r)
		d.addCallback(got1)
		d.addCallback(got2)
		def cmt(_):
			e = self.store.commit()
			e.addCallback(lambda x: _)
			return e
		def rlb(_):
			e = self.store.rollback()
			e.addBoth(lambda x: _)
			return e
		d.addCallback(cmt)
		d.addErrback(rlb)
		return d

	def set(self, key, val):
		e = DbTable()
		e.category = self.category
		e.name = repr(key)
		e.value = repr(val)
		d = self.store.add(e)
		def cmt(_):
			e = self.store.commit()
			e.addCallback(lambda x: _)
			return e
		def rlb(_):
			e = self.store.rollback()
			e.addBoth(lambda x: _)
			return e
		d.addCallback(cmt)
		d.addErrback(rlb)
		return d
	


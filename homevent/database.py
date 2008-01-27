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
from twisted.internet.defer import inlineCallbacks,returnValue

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
	
	@inlineCallbacks
	def get(self, key):
		try:
			r = yield self.store.find(DbTable,
				DbTable.category == self.category,
				DbTable.name == repr(key))
			r = yield r.one()
			r = r.value
			r = eval(r,SafeNames,{})
			yield self.store.commit()
			returnValue(r)
		except BaseException,e:
			yield self.store.rollback()
			raise e

	@inlineCallbacks
	def delete(self, key):
		try:
			r = yield self.store.find(DbTable,
				DbTable.category == self.category,
				DbTable.name == repr(key))
			r = yield r.one()
			yield self.store.remove(r)
			yield self.store.commit()
		except BaseException,e:
			yield self.store.rollback()
			raise e

	@inlineCallbacks
	def set(self, key, val):
		try:
			e = DbTable()
			e.category = self.category
			e.name = repr(key)
			e.value = repr(val)

			yield self.store.add(e)
			yield self.store.commit()
		except BaseException,e:
			yield self.store.rollback()
			raise e
	


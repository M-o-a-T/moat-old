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
from storm.twisted.store import DeferredStore,StorePool

from twisted.internet.defer import inlineCallbacks,returnValue

SafeNames = {
	"Name":Name,
}

from he_storage import DbTable,database

#Db = DeferredStore(self.database)

class DbStore(object):
	"""This object implements a simple Deferred-enabled storage"""
	def __init__(self,cat):
		self.pool = StorePool(database, 2, 5)
		self.category = repr(cat)
	
	def start(self):
		return self.pool.start()
	
	def stop(self):
		return self.pool.stop()
	
	@inlineCallbacks
	def get(self, key):
		store = yield self.pool.get()
		try:
			r = yield store.find(DbTable,
				DbTable.category == self.category,
				DbTable.name == repr(key))
			r = yield r.one()
			if r is None:
				raise KeyError(key)
			r = r.value
			r = eval(r,SafeNames,{})
			yield store.commit()
			returnValue(r)
		except BaseException,e:
			yield store.rollback()
			raise e
		finally:
			self.pool.put(store)

	@inlineCallbacks
	def all(self, callback):
		store = yield self.pool.get()
		try:
			r = yield store.find(DbTable,
				DbTable.category == self.category)

			def call_it(r):
				for info in r:
					callback(r)
			yield store.thread.deferToThread(call_it,r)
		except BaseException,e:
			yield store.rollback()
			raise e
		finally:
			self.pool.put(store)

	@inlineCallbacks
	def delete(self, key):
		store = yield self.pool.get()
		try:
			r = yield store.find(DbTable,
				DbTable.category == self.category,
				DbTable.name == repr(key))
			r = yield r.one()
			if r is None:
				raise KeyError(key)
			yield store.remove(r)
			yield store.commit()
		except BaseException,e:
			yield store.rollback()
			raise e
		finally:
			self.pool.put(store)

	@inlineCallbacks
	def set(self, key, val):
		store = yield self.pool.get()
		try:
			e = yield store.find(DbTable,
				DbTable.category == self.category,
				DbTable.name == repr(key))
			e = yield e.one()
			if e is None:
				e = DbTable()
				e.category = self.category
				e.name = repr(key)
				yield store.add(e)
			e.value = repr(val)
			yield store.commit()
		except BaseException,e:
			yield store.rollback()
			raise e
		finally:
			self.pool.put(store)
	

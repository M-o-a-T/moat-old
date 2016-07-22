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

"""\
This is the core of database access.
"""

from moat import TESTING
from moat.base import Name
from moat.logging import log,TRACE
from sqlmix import Db,NoData,ManyData

SafeNames = {
	"Name":Name,
}

#Db = DeferredStore(self.database)

class DbStore(object):
	"""This object implements a simple Deferred-enabled storage"""
	running = False

	def __init__(self,category,name=None):
		if name is None:
			if TESTING:
				name = "MOAT_TEST"
			else:
				name = "MOAT"
		if TESTING:
			def trace(a,b,c):
				log(TRACE,a,b,c)
		else:
			trace = None

		self.db = Db(name, trace=trace)
		self.category = " ".join(Name(category)).encode("utf-8")
		db=self.db()
		try:
			db.Do("CREATE TABLE HE_State ("
			  " category varchar(50),"
			  " name varchar(200),"
			  " value BLOB,"
			  " id INTEGER AUTO_INCREMENT PRIMARY KEY,"
		      " UNIQUE (category,name))", _empty=1)
		except Exception:
			try:
			    db.Do("CREATE TABLE HE_State ("
			      " category varchar(50),"
			      " name varchar(200),"
			      " value BLOB,"
			      " id INTEGER PRIMARY KEY,"
		          " UNIQUE (category,name))", _empty=1)
			except Exception:
				pass
		
		self.running = True
	
	def close(self):
		self.db.close()
		self.db = None

	def get(self, key):
		key = " ".join(Name(key)).encode("utf-8")
		with self.db() as db:
			try:
				r, = db.DoFn("select value from HE_State where category=${cat} and name=${name}", cat=self.category, name=key)
			except NoData:
				raise KeyError((self.category,key))
			else:
				r = eval(r,SafeNames,{})
		return r

	def all(self, callback):
		with self.db() as db:
			return db.DoSelect("select name,value from HE_State where category=${cat}", cat=self.category, callback=callback)

	def delete(self, key):
		key = " ".join(Name(key)).encode("utf-8")
		with self.db() as db:
			try:
				db.Do("delete from HE_State where category=${cat} and name=${name}", cat=self.category,name=key)
			except NoData:
				raise KeyError((self.category,key))

	def clear(self):
		with self.db() as db:
			return db.Do("delete from HE_State where category=${cat}", cat=self.category, _empty=1)

	def set(self, key, val):
		key = " ".join(Name(key)).encode("utf-8")
		with self.db() as db:
			r = db.Do("update HE_State set value=${val} where category=${cat} and name=${name}", cat=self.category,name=key,val=repr(val), _empty=1)
			if r == 0:
				db.Do("insert into HE_State (category,name,value) VALUES(${cat},${name},${val})", cat=self.category,name=key,val=repr(val))

	

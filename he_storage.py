#!/usr/bin/python
# -*- coding: utf-8 -*-

##########################################################
## Make sure that this file is not readable by anybody! ##
## It contains the database password.                   ##
##########################################################

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

## This file is expected to export:

## * a DbTable class with (raw) string attributes "category","name" and "value"
## * a database instance
##

from storm.properties import Int,RawStr
from storm.database import create_database
__all__ = ("DbTable","database")

class DbTable(object):
	__storm_table__ = "HE_State"
	id = Int(primary=True)
	category = RawStr()
	name = RawStr()
	value = RawStr()

#database = create_database("backend://username:password@hostname/database_name")

import os
if "HOMEVENT_TEST" in os.environ:
	dbf = "/tmp/homevent.db.%d" % (os.getuid(),)
else:
	dbf = "/var/lib/homevent/state.db"

if os.path.exists(dbf):
	database = create_database("sqlite:"+dbf)
else:
	database = create_database("sqlite:"+dbf)
	conn = database.connect()
	conn.execute("CREATE TABLE HE_State ("
	             " category BLOB,"
	             " name BLOB,"
	             " value BLOB,"
	             " id INTEGER PRIMARY KEY)")
	conn.commit()
	del conn

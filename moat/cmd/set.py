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

"""List of known Tasks"""

import os
from moat.script import Command, SubCommand, CommandError
import aio_etcd as etcd
import logging
logger = logging.getLogger(__name__)

__all__ = ['SetCommand']

class EtcdCommand(Command):
	name = "etcd"
	summary = "Update etcd data"""
	description = """\
Add/Update/Delete etcd contents.

Usage (unless deleting): path.to.entry=value
If you want to modify an entry, the '-m' or '-p' option is mandatory.

"""

	def addOptions(self):
		self.parser.add_option('-a','--append',
            action="store_true", dest="append",
            help="append a unique entry")
		self.parser.add_option('-d','--delete',
            action="store_true", dest="delete",
            help="delete entries instead of updating them")
		self.parser.add_option('-u','--update',
            action="store_true", dest="update",
            help="update an entry. Implied when old value or modstamp is given")
		self.parser.add_option('-m','--modified',
            action="store", dest="modified",
            help="Modification stamp of current entry.")
		self.parser.add_option('-p','--prev',
            action="store", dest="previous",
            help="Previous value of current entry.")

	def handleOptions(self):
		opts = self.options
		if (opts.delete or opts.modified or opts.previous) and opts.append:
			raise CommandError("Conflicting arguments")
		self.delete = opts.delete
		self.modified = opts.modified
		self.previous = opts.previous
		self.append = opts.append
		self.create = not opts.update

	async def do(self,args):
		if not args:
			raise CommandError("Not specifying values to %s makes no sense." % ("delete" if self.delete else "add/update"))
		etc = await self.root._get_etcd()
		retval = 0
		if self.delete:
			if not self.create:
				raise CommandError("You can't update and delete at the same time.")
			for a in args:
				pa = a.replace('.','/')
				kw = {}
				if self.modified:
					kw['prevIndex'] = self.modified
				if self.previous:
					kw['prevValue'] = self.previous
				try:
					await etc.delete('/'+pa, recursive=True,**kw)
				except etcd.EtcdCompareFailed:
					logger.fatal("Bad modstamp: "+a)
					retval = 1
				except etcd.EtcdKeyNotFound:
					logger.info("Key already deleted: "+a)
		else:
			for a in args:
				a,v = a.split('=',1)
				pa = a.replace('.','/')
				create=self.create
				try:
					kw={}
					if self.modified:
						kw['index']=self.modified
						create=False
					if self.previous:
						kw['prev']=self.previous
						create=False
					if v:
						kw['value']=v
					if self.append:
						kw['append']=True
						create=True
					r = await etc.set('/'+pa, create=create, **kw)
					if self.append:
						print(r.key.rsplit('/',1)[1], file=self.stdout)
				except etcd.EtcdCompareFailed:
					logger.error("Bad modstamp: "+a)
					retval = 1
				except etcd.EtcdAlreadyExist:
					logger.error("Entry exists: "+a)
					retval = 1
		return retval

class DevCommand(Command):
	name = "dev"
	summary = "Update device data"""
	description = """\
Add/Update/Delete device attributes.

Usage: path/to/device input/name entry=value  -- modify an entry
       path/to/device input/name -d entry     -- delete this entry

Of course you can use "output" instead of "input", if the device has any.
See "moat show dev --help" for displaying values.

"""

	def addOptions(self):
		self.parser.add_option('-d','--delete',
            action="store_true", dest="delete",
            help="delete entries instead of adding/updating them")

	def handleOptions(self):
		opts = self.options
		self.delete = opts.delete

	async def do(self,args):
		if not args:
			raise CommandError("Not specifying values to %s makes no sense." % ("delete" if self.delete else "add/update"))
		etc = await self.root._get_etcd()
		retval = 0
		if self.delete:
			if not self.create:
				raise CommandError("You can't update and delete at the same time.")
			for a in args:
				pa = a.replace('.','/')
				kw = {}
				if self.modified:
					kw['prevIndex'] = self.modified
				if self.previous:
					kw['prevValue'] = self.previous
				try:
					await etc.delete('/'+pa, recursive=True,**kw)
				except etcd.EtcdCompareFailed:
					logger.fatal("Bad modstamp: "+a)
					retval = 1
				except etcd.EtcdKeyNotFound:
					logger.info("Key already deleted: "+a)
		else:
			for a in args:
				a,v = a.split('=',1)
				pa = a.replace('.','/')
				create=self.create
				try:
					kw={}
					if self.modified:
						kw['index']=self.modified
						create=False
					if self.previous:
						kw['prev']=self.previous
						create=False
					if v:
						kw['value']=v
					if self.append:
						kw['append']=True
						create=True
					r = await etc.set('/'+pa, create=create, **kw)
					if self.append:
						print(r.key.rsplit('/',1)[1], file=self.stdout)
				except etcd.EtcdCompareFailed:
					logger.error("Bad modstamp: "+a)
					retval = 1
				except etcd.EtcdAlreadyExist:
					logger.error("Entry exists: "+a)
					retval = 1
		return retval

class SetCommand(SubCommand):
	name = "set"
	summary = "Update data"""
	description = """\
Set some data.
"""

	subCommandClasses = [EtcdCommand, DevCommand]


# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

"""Handle event logging for graphing"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import types
from pprint import pprint
from sqlmix.async import Db,NoData
from qbroker.unit import CC_DICT, CC_DATA, CC_MSG
from yaml import dump
from traceback import print_exc
from boltons.iterutils import remap

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK

import logging
logger = logging.getLogger(__name__)

## DO NOT change the numbers
modes = {
	0: ('ignore', "keep data of this type, but ignore them"),
	1: ('delete', "remove values of this type"),
	2: ('store', "Continuous value (power use, temperature, humidity)"),
	3: ('count', "Increasing discrete value (rain gauge, lightning counter)"),
	4: ('cont', "Increasing continuous value (power meter)"),
	5: ('event', "Single event (button pressed)"),
	6: ('cycle', "Cyclic value (wind direction)"),
}

__all__ = ['GraphCommand']

## TODO add --dest UUID

class LogCommand(Command):
	name = "log"
	summary = "Log the event stream from AMQP to SQL",
	description = """\
Log the event stream from AMQP to SQL

"""
	async def do(self,args):
		if len(args):
			raise SyntaxError("Usage: log")
		self.u = await self.root._get_amqp()
		await self.u.register_alert_async('#', self.callback, durable='log_mysql', call_conv=CC_MSG)
		self.db = Db(**self.cfg['config']['sql']['data_logger']['server'])
		self.prefix=u.config['sql']['data_logger']['prefix']

		while True:
			await asyncio.sleep(999,loop=self.loop)

	async def callback(self, msg):
		try:
			body = msg.data

			dep = '?' if body.get('deprecated',False) else '.'
			val = body.get('value',None)
			if val is None:
				return
			try:
				val = float(val)
			except ValueError:
				if val.lower() == "on":
					val = 1
				elif val.lower == "off":
					val = 0
				else:
					if self.root.verbose:
						pprint.pprint(body)
					return
			try:
				nam = ' '.join(body['event'])
			except KeyError:
				if self.root.verbose:
					pprint.pprint(body)
				return

			#print(dep,val,nam)
			async with self.db() as d:
				try:
					tid, = await d.DoFn("select id from %stype where tag=${name}"%(self.prefix,), name=nam,)
				except NoData:
					tid = await d.Do("insert into %stype set tag=${name}"%(self.prefix,), name=nam,)
				f = await d.Do("insert into %slog set value=${value},data_type=${tid},timestamp=from_unixtime(${ts})"%(self.prefix,), value=val,tid=tid, ts=msg.timestamp)
				if self.root.verbose:
					print(dep,val,nam)

		except Exception as exc:
			logger.exception("Problem processing %s", repr(body))
			quitting.set()

class ListCommand(Command):
	name = "list"
	summary = "show graph states"
	description = """\
This command shows the status of current graphing 

"""

	def addOptions(self):
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", default=-1,
			help="Show this aggregation layer")
		self.parser.add_option('-u','--unassigned',
			action="store_true", dest="unassigned",
			help="Show new data types")
		self.parser.add_option('-n','--last',
			action="store", type="int", dest="last",
			help="Show the last N records")

	async def do(self,args):
		self.u = await self.root._get_amqp()
		self.db = Db(**self.root.cfg['config']['sql']['data_logger']['server'])

		async with self.db() as db:
			if self.options.unassigned:
				if self.options.layer >= 0:
					raise SyntaxError("You can't use '-u' with a specific layer")
				if args:
					raise SyntaxError("You can't use '-u' with a specific type")
				await self._do_unassigned(db)
			elif args:
				await self._do_args(db,args)
			else:
				await self._do_other(db,)

	async def _do_unassigned(self,db):
		seen = False
		
		if self.options.last:
			async for d in db.DoSelect("select data_log.*,data_type.tag from data_log join data_type on data_type.id=data_log.data_type where data_type.method is null order by data_log.timestamp desc limit ${limit}", _dict=True, limit=self.options.last):
				if self.root.verbose > 1:
					if seen:
						print("===")
					pprint(remap(d, lambda p, k, v: v is not None))
				else:
					print(d['timestamp'],d['tag'],d['value'], sep='\t')
				seen = True
		else:
			async for d in db.DoSelect("select * from data_type where method is null order by tag", _dict=True):
				if self.root.verbose > 1:
					if seen:
						print("===")
					pprint(remap(d, lambda p, k, v: v is not None))
				else:
					print(d['timestamp'],d['tag'], sep='\t')
				seen = True

		if not seen:
			print("No unassigned data. Great!")

	async def _do_args(self,db, args):
		dtid, = await self.db.DoFn("select id from data_type where tag=${tag}", tag=' '.join(args))
		if self.options.last:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_log where data_log.data_type=${id} order by data_log.timestamp desc limit ${limit}", _dict=True, id=dtid, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['value'], sep='\t')
					seen = True
			else:
				async for d in db.DoSelect("select data_agg.* from data_agg join data_agg_type on data_agg.data_agg_type=data_agg_type.id where data_agg_type.data_type=${id} order by data_agg.timestamp desc limit ${limit}", _dict=True, id=dtid, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['data_agg.timestamp'],d['data_agg.value'], sep='\t')
					seen = True
			if not seen:
				print("No data?")

		else:
			if self.options.layer < 0: # display this type
				d = await self.db.DoFn("select * from data_type where id=${id}", _dict=True, id=dtid)
				pprint(remap(d, lambda p, k, v: v is not None))
			else: # display this layer
				d = await self.db.DoFn("select * from data_agg_type where data_type=${id} and layer=${layer}", _dict=True, id=dtid, layer=self.options.layer)
				pprint(remap(d, lambda p, k, v: v is not None))

	async def _do_other(self,db):
		seen = False

		if self.options.last:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_log where data_type=${id} order by data_log.timestamp desc limit ${limit}", _dict=True, limit=self.options.last, id=dtid):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['value'], sep='\t')
					seen = True
			else:
				async for d in db.DoSelect("select data_agg.* from data_agg join data_agg_type on data_agg.data_agg_type=data_agg_type.id where data_agg_type.data_type=${id} and data_agg_type.layer=${layer} order by data_agg.timestamp desc limit ${limit}", _dict=True, id=dtid, layer=self.options.layer, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['data_agg_log.timestamp'],d['data_agg_log.value'], sep='\t')
					seen = True
		else:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_type", _dict=True):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['tag'], sep='\t')
					seen = True
			else:
				async for d in db.DoFn("select data_agg_type.*,data_type.tag from data_agg_type join data_type on data_type.id=data_agg_type.data_type where layer=${layer}", _dict=True, layer=self.options.layer):
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['tag'], sep='\t')
					seen = True
		if not seen:
			print("No data?")

class SetCommand(Command):
	name = "set"
	summary = "Set data type and aggregation"
	description = """\
Set data type and aggregation options for a logged event type
"""

	def addOptions(self):
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", default=-1,
			help="Show this aggregation layer")
		self.parser.add_option('-m','--mode',
			action="store", dest="mode",
			help="set mode (%s)" % ','.join(x[0] for x in modes.values()))
		self.parser.epilog = "Modes:\n"+"\n".join("%s\t%s"%(a,b) for a,b in modes.values())

	async def do(self,args):
		if not args:
			raise SyntaxError("Usage: set [options] data_tag")
		args = ' '.join(args)
		if self.options.mode:
			try:
				mode = modes[self.options.mode]
			except KeyError:
				raise SyntaxError("Unknown mode '%s'" % self.options.mode)
		else:
			mode = None

		if self.options.layer < 0:
			pass
		else:
			if mode is not None:
				raise SyntaxError("You can't set modes for a layer")

class LayerCommand(Command):
	name = "layer"
	summary = "Set layer options"
	description = """\
Create an aggregation layer and/or set options
"""

	def addOptions(self):
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", default=-1,
			help="Show this aggregation layer")
		self.parser.add_option('-i','--interval',
			action="store", dest="interval",
			help="interval to aggregate into")
		self.parser.add_option('-m','--maxage',
			action="store", dest="max_age",
			help="max age of data")


	async def do(self,args):
		if not args or self.options.layer < 0:
			raise SyntaxError("Usage: set -l LAYER [options] data_tag")
		args = ' '.join(args)
		dtid, = await self.db.DoFn("select id from data_type where tag=${tag}", tag=' '.join(args))

		try:
			iid,intv = await self.db.DoFn("select id from data_agg_type where data_type=${id} and layer=${layer}", id=dtid,layer=self.options.layer)
		except NoData:
			if not self.options.interval:
				raise SyntaxError("The interval must be specified")
			iid=None
			intv = self.options.interval
			if self.options.layer > 0:
				try:
					lid,lint = await self.db.DoFn("select id,interval from data_agg_type where data_type=${id} and layer=${layer}", id=dtid,layer=self.options.layer-1)
				except NoData:
					raise SyntaxError("Layers need to be contiguous")
				else:
					if self.options.interval % lint:
						raise SyntaxError("The interval must be a multiple of the next-lower layer's interval")
		else:
			if self.options.interval:
				raise SyntaxError("The interval cannot be changed")
			
		upd = {}
		if self.options.interval:
			upd['interval'] = self.options.interval
		if self.options.max_age:
			if self.options.max_age < 3*intv:
				raise SyntaxError("maxage is too low, this makes no sense")
			upd['max_age'] = self.options.max_age
		if not upd:
			raise SyntaxError("No change specified")

		if iid is None:
			await db.Do("insert into data_agg_type ("+','.join("%s"%(k,) for k in upd.keys())+") values ("+','.join("${$%s}"%(k,) for k in upd.keys())+")", id=iid, **upd)
		else:
			await db.Do("update data_agg_type set "+','.join("%s=${$%s}"%(k,k) for k in upd.keys())+" where id=${id}", id=iid, **upd)

class GraphCommand(SubCommand):
	name = "graph"
	summary = "Handle event logging and aggregation for graphs"
	description = """\
Commands to manipulate logging events for graphing etc.
"""

	# process in order
	subCommandClasses = [
		ListCommand,
		LogCommand,
		SetCommand,
		LayerCommand,
	]



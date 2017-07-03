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
from datetime import datetime

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK
from moat.times import simple_time_delta, humandelta
from . import modes,modenames

import logging
logger = logging.getLogger(__name__)

__all__ = ['GraphCommand']

## TODO add --dest UUID

def add_human(d):
	"""add human-readable tags"""
	for k in "interval max_age".split():
		v = d.get(k,None)
		if v is not None:
			d.setdefault('human',{})[k] = humandelta(v)
	m = d.get('method',None)
	if m is not None:
		d.setdefault('human',{})['method'] = modes[m]



class _Command(Command):
	async def setup(self):
		self.db = Db(**self.root.cfg['config']['sql']['data_logger']['server'])

class LogCommand(_Command):
	name = "log"
	summary = "Log the event stream from AMQP to SQL"
	description = """\
Log the event stream from AMQP to SQL

"""
	async def do(self,args):
		if len(args):
			raise SyntaxError("Usage: log")
		await self.setup()

		self.u = await self.root._get_amqp()
		await self.u.register_alert_async('#', self.callback, durable='log_mysql', call_conv=CC_MSG)

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
				await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
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

class ListCommand(_Command):
	name = "list"
	summary = "show graph states"
	description = """\
This command shows the status of current graphing 

"""

	def addOptions(self):
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", type="int", default=-1,
			help="Show this aggregation layer")
		self.parser.add_option('-L','--all-layers',
			action="store_const", dest="layer", const=-2,
			help="Show all aggregation layers")
		self.parser.add_option('-u','--unassigned',
			action="store_true", dest="unassigned",
			help="Show new data types")
		self.parser.add_option('-m','--method',
			action="store", dest="method",
			help="limit to this method (all,%s)" % ','.join(x[0] for x in modes.values()))
		self.parser.add_option('-n','--last',
			action="store", type="int", dest="last",
			help="Show the last N records")

	async def do(self,args):
		self.u = await self.root._get_amqp()
		await self.setup()

		try:
			async with self.db() as db:
				await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
				if self.options.unassigned or self.options.method:
					if self.options.layer >= 0:
						raise SyntaxError("You can't use '-u'/'-m' with a specific layer")
					if args:
						raise SyntaxError("You can't use '-u'/'-m' with a specific type")
					await self._do_unassigned(db, None if self.options.unassigned else self.options.method)
				elif args:
					await self._do_args(db,args)
				else:
					await self._do_other(db,)
		except NoData:
			print("… no data.", file=sys.stderr)

	async def _do_unassigned(self,db,method):
		seen = False
		
		if method is None:
			mf = "IS NULL"
		elif method == "all":
			mf = "IS NOT NULL"
		else:
			mf = "= ${method}"
			try:
				method = modenames[method]
			except KeyError:
				print("Unknown method. Known:",' '.join(sorted(modenames.keys())), file=sys.stderr)
				return
		if self.options.last:
			async for d in db.DoSelect("select data_log.*,data_type.tag from data_log join data_type on data_type.id=data_log.data_type where data_type.method %s order by data_log.timestamp desc limit ${limit}" % (mf,), _dict=True, limit=self.options.last, method=method):
				if self.root.verbose > 1:
					if seen:
						print("===")
					add_human(d)
					pprint(remap(d, lambda p, k, v: v is not None))
				else:
					print(d['timestamp'],d['tag'],d['value'], sep='\t')
				seen = True
		else:
			async for d in db.DoSelect("select * from data_type where method %s and timestamp > '1999-12-31'  order by n_values desc,tag" % (mf,), _dict=True, method=method):
				add_human(d)
				if self.root.verbose > 1:
					if seen:
						print("===")
					pprint(remap(d, lambda p, k, v: v is not None))
				else:
					print(d['n_values'],d['human']['method'][0],d['timestamp'],d['tag'], sep='\t')
				seen = True

	async def _do_args(self,db, args):
		seen = False

		dtid, = await self.db.DoFn("select id from data_type where tag=${tag}", tag=' '.join(args))
		if self.options.last:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_log where data_log.data_type=${id} order by data_log.timestamp desc limit ${limit}", _dict=True, id=dtid, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						add_human(d)
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['value'], sep='\t')
					seen = True
			else:
				async for d in db.DoSelect("select data_agg.* from data_agg join data_agg_type on data_agg.data_agg_type=data_agg_type.id where data_agg_type.data_type=${id} order by data_agg.timestamp desc limit ${limit}", _dict=True, id=dtid, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						add_human(d)
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['value'],d['n_values'], sep='\t')
					seen = True
			if not seen:
				print("No data?")

		else:
			if self.options.layer < 0: # display this type
				d = await self.db.DoFn("select * from data_type where id=${id}", _dict=True, id=dtid)
				if self.options.layer < -1:
					await self.ext_layer(db,d)
				add_human(d)
				pprint(remap(d, lambda p, k, v: v is not None))
			else: # display this layer
				d = await self.db.DoFn("select * from data_agg_type where data_type=${id} and layer=${layer}", _dict=True, id=dtid, layer=self.options.layer)
				add_human(d)
				pprint(remap(d, lambda p, k, v: v is not None))

	async def ext_layer(self,db,d):
		d['layers'] = dl = []
		async for dx in db.DoSelect("select * from data_agg_type where data_type=${dtid} order by layer", dtid=d['id'], _dict=True):
			add_human(dx)
			dl.append(dx)

	async def _do_other(self,db):
		seen = False

		if self.options.last:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_log where data_type=${id} order by data_log.timestamp desc limit ${limit}", _dict=True, limit=self.options.last, id=dtid):
					if self.root.verbose > 1:
						if seen:
							print("===")
						if self.options.layer < -1:
							await self.ext_layer(db,d)
						add_human(d)
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['value'], sep='\t')
					seen = True
			else:
				async for d in db.DoSelect("select data_agg.* from data_agg join data_agg_type on data_agg.data_agg_type=data_agg_type.id where data_agg_type.data_type=${id} and data_agg_type.layer=${layer} order by data_agg.timestamp desc limit ${limit}", _dict=True, id=dtid, layer=self.options.layer, limit=self.options.last):
					if self.root.verbose > 1:
						if seen:
							print("===")
						add_human(d)
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['data_agg_log.timestamp'],d['data_agg_log.value'], sep='\t')
					seen = True
		else:
			if self.options.layer < 0:
				async for d in db.DoSelect("select * from data_type", _dict=True):
					add_human(d)
					if self.root.verbose > 1:
						if seen:
							print("===")
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['n_values'],d['human']['method'][0],d['timestamp'],d['tag'], sep='\t')
					seen = True
			else:
				async for d in db.DoSelect("select data_agg_type.*,data_type.tag from data_agg_type join data_type on data_type.id=data_agg_type.data_type where layer=${layer}", _dict=True, layer=self.options.layer):
					if self.root.verbose > 1:
						if seen:
							print("===")
						add_human(d)
						pprint(remap(d, lambda p, k, v: v is not None))
					else:
						print(d['timestamp'],d['tag'], sep='\t')
					seen = True
		if not seen:
			print("No data?")

class SetCommand(_Command):
	name = "set"
	summary = "Set data type and aggregation"
	description = """\
Set data type and aggregation options for a logged event type
"""

	def addOptions(self):
		self.parser.add_option('-m','--method',
			action="store", dest="method",
			help="set method (%s)" % ','.join(x[0] for x in modes.values()))
		self.parser.add_option('-u','--unit',
			action="store", dest="unit",
			help="set the entry's unit (°C, m/s, …)")
		self.parser.add_option('-s','--sort',
			action="store", dest="order", type=int,
			help="set the type's sort priority (higher is earlier)")
		self.parser.add_option('-f','--factor',
			action="store", dest="factor",
			help="set the entry's factor (1024, 1000, …)")
		self.parser.add_option('-F','--force',
			action="store_true", dest="force",
			help="Yes, I do want to set the type, no matter what")
		self.parser.add_option('-n','--name',
			action="store", dest="name",
			help="name the entry (for display)")
		self.parser.epilog = "Methods:\n"+"\n".join("%s\t%s"%(a,b) for a,b in modes.values())

	async def do(self,args):
		if not args:
			raise SyntaxError("Usage: set [options] data_tag")
		await self.setup()

		async with self.db() as db:
			await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
			dtid, = await db.DoFn("select id from data_type where tag=${tag}", tag=' '.join(args))
			if self.options.method:
				try:
					method = modenames[self.options.method]
				except KeyError:
					raise SyntaxError("Unknown method '%s'" % self.options.method)
			else:
				method = None

			omethod, = await db.DoFn("select method from data_type where id=${id}", id=dtid)
			tcnt, = await db.DoFn("select count(*) from data_agg_type where data_type=${id}", id=dtid)
			if method is not None and omethod is not None and method != omethod and tcnt > 0 and not self.options.force:
				raise RuntimeError("You cannot change the method after the fact")
			upd = {}
			if method is not None:
				upd['method'] = method
			if self.options.unit:
				upd['display_unit'] = self.options.unit
			if self.options.factor:
				upd['display_factor'] = self.options.factor
			if self.options.name:
				upd['display_name'] = self.options.name
			if self.options.order:
				upd['display_order'] = self.options.order

			if upd:
				try:
					await db.Do("update data_type set "+','.join("%s=${%s}"%(k,k) for k in upd.keys())+" where id=${id}", id=dtid, **upd)
				except NoData:
					if self.root.verbose:
						print("no change")
				else:
					if self.root.verbose:
						print("OK")
			else:
				raise SyntaxError("Nothing to change.")

class ResetCommand(_Command):
	name = "reset"
	summary = "Clear accumulated aggregation"
	description = """\
Set data type and aggregation options for a logged event type
"""

	def addOptions(self):
		self.parser.add_option('-m','--method',
			action="store", dest="method",
			help="set method (%s)" % ','.join(x[0] for x in modes.values()))
		self.parser.add_option('-F','--force',
			action="store_true", dest="force",
			help="Yes, I do want to delete data")
		self.parser.add_option('-L','--layers',
			action="store_true", dest="layers",
			help="Also delete layer data and reset mode")

	async def do(self,args):
		if not args:
			raise SyntaxError("Usage: reset [options] data_tag")
		if not self.options.force:
			raise SyntaxError("No delety without forcy")
		await self.setup()

		async with self.db() as db:
			await db.Do("SET TIME_ZONE='+00:00'", _empty=True)

			dtid, = await db.DoFn("select id from data_type where tag=${tag}", tag=' '.join(args))
			async for tid, in db.DoSelect("select id from data_agg_type where data_type=${dtid}", dtid=dtid):
				await db.Do("delete from data_agg where data_agg_type=${tid}", tid=tid, _empty=True)
			if self.options.layers:
				await db.Do("delete from data_agg_type where data_type=${dtid}", dtid=dtid, _empty=True)
				await db.Do("update data_type set method=NULL where id=${dtid}", dtid=dtid, _empty=True)
			else:
				await db.Do("update data_agg_type set timestamp='1999-01-01', ts_last='1999-01-01', value=0, aux_value=0 where data_type=${dtid}", dtid=dtid, _empty=True)

class LayerCommand(_Command):
	name = "layer"
	summary = "Set layer options"
	description = """\
Create an aggregation layer and/or set options
"""

	def addOptions(self):
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", type=int, default=-1,
			help="Show this aggregation layer")
		self.parser.add_option('-i','--interval',
			action="store", dest="interval",
			help="interval to aggregate into")
		self.parser.add_option('-m','--maxage',
			action="store", dest="max_age",
			help="max age of data")
		self.parser.add_option('-c','--copy',
			action="store", dest="copy",
			help="copy layer data from this entry")

	async def do(self,args):
		if not args or (self.options.layer < 0 and not self.options.copy):
			raise SyntaxError("Usage: set -l LAYER [options] data_tag")
		tag = ' '.join(args)
		await self.setup()

		if self.options.copy:
			if self.options.interval or self.options.max_age:
				raise SyntaxError("Copying and setting parameters is not compatible")
		if self.options.interval:
			self.options.interval = simple_time_delta(self.options.interval)
		async with self.db() as db:
			await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
			try:
				dtid, = await db.DoFn("select id from data_type where tag=${tag}", tag=tag)
			except NoData:
				raise SyntaxError("Tag '%s' unknown" % (tag,))
			upd = {}

			if self.options.copy:
				try:
					cdtid, = await db.DoFn("select id from data_type where tag=${tag}", tag=self.options.copy)
				except NoData:
					raise SyntaxError("Source tag unknown")
				if self.options.layer < 0:
					c, = await db.DoFn("select count(*) from data_agg_type where data_type=${id}", id=dtid)
					if c > 0:
						raise SyntaxError("Some layers already exist, copy separately.")
					from .process import agg_type
					t = agg_type(self,db)
					async for d in db.DoSelect("select * from data_agg_type where data_type=${dtid}", dtid=cdtid, _dict=True):
						await t.set(d)
						t.data_type = dtid
						t.id = None
						t.ts_last = t.timestamp = datetime(1999,1,1,0,0,0)
						await t.save()
					return
			try:
				iid,intv = await db.DoFn("select id,`interval` from data_agg_type where data_type=${id} and layer=${layer}", id=dtid, layer=self.options.layer)
			except NoData:
				if not self.options.interval:
					raise SyntaxError("The interval must be specified")
				upd['interval'] = intv = self.options.interval
				iid=None

				if self.options.layer > 0:
					try:
						lid,lint = await db.DoFn("select id,`interval` from data_agg_type where data_type=${id} and layer=${layer}", id=dtid,layer=self.options.layer-1)
					except NoData:
						raise SyntaxError("Layers need to be contiguous")
					else:
						if self.options.interval % lint:
							raise SyntaxError("The interval must be a multiple of the next-lower layer's interval")
				upd['layer'] = self.options.layer
			else:
				if self.options.interval:
					raise SyntaxError("The interval cannot be changed")
				
			if self.options.max_age:
				if self.options.max_age == '-':
					max_age = None
				else:
					max_age = simple_time_delta(self.options.max_age)
					if max_age < 3*intv:
						raise SyntaxError("maxage is too low, this makes no sense")
				upd['max_age'] = max_age
			if not upd:
				raise SyntaxError("No change specified")

			if iid is None:
				upd['data_type'] = dtid
			ks = list(upd.keys())
			if iid is None:
				await db.Do("insert into data_agg_type ("+','.join("`%s`"%(k,) for k in ks)+") values ("+','.join("${%s}"%(k,) for k in ks)+")", **upd)
			else:
				await db.Do("update data_agg_type set "+','.join("`%s`=${%s}"%(k,k) for k in ks)+" where id=${id}", id=iid, **upd)

class RunCommand(_Command):
	name = "run"
	summary = "Run layer processing"
	description = """\
Process a layer (or all of them)
"""

	def addOptions(self):
		self.parser.add_option('-n','--no-clean',
			action="store_true", dest="noclean",
			help="don't run clean-up code")
		self.parser.add_option('-l','--layer',
			action="store", dest="layer", type=int, default=-1,
			help="Run only this aggregation layer")

	async def do(self,args):
		from .process import agg_type
		tag = ' '.join(args)
		await self.setup()

		todo = []
		async with self.db() as db:
			await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
			filter = {}
			if tag:
				filter['data_type'], = await db.DoFn("select id from data_type where tag=${tag}", tag=tag)
			if self.options.layer >= 0:
				filter['layer'] = self.options.layer
			fs = ' and '.join("`%s`=${%s}" % (k,k) for k in filter.keys())
			if fs:
				fs = " where "+fs
			fs += " order by layer,timestamp"

			async for d in db.DoSelect("select * from data_agg_type"+fs, **filter, _dict=True):
				todo.append(d)
		for d in todo:
			async with self.db() as db:
				await db.Do("SET TIME_ZONE='+00:00'", _empty=True)
				at = agg_type(self,db)
				await at.set(d)
				logger.info("Run %s:%d",at.tag,at.layer)
				await at.run(cleanup=not self.options.noclean)

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
		ResetCommand,
		LayerCommand,
		RunCommand,
	]



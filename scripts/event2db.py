#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
## This file is part of QBroker, an easy to use RPC and broadcast
## client+server using AMQP.
##
## QBroker is Copyright © 2016 by Matthias Urlichs <matthias@urlichs.de>,
## it is licensed under the GPLv3. See the file `README.rst` for details,
## including optimistic statements by the author.
##
## This paragraph is auto-generated and may self-destruct at any time,
## courtesy of "make update". The original is in ‘utils/_boilerplate.py’.
## Thus, please do not remove the next line, or insert any blank lines.
##BP

import asyncio
from qbroker.unit import Unit, CC_DATA, CC_MSG
from qbroker.util.tests import load_cfg
import signal
import pprint
import json
from sqlmix.async_ import Db,NoData
from time import time

import logging
import sys
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

import os
if len(sys.argv) != 2:
	print("Usage: %s cfgname" % (sys.argv[0],), file=sys.stderr)
	sys.exit(1)
cfg = sys.argv[1]
u=Unit("qbroker.monitor", **load_cfg(cfg)['config'])
cf=u.config['amqp']['server']
print(cf['host'],cf['virtualhost'])
db=Db(**u.config['sql']['data_logger']['server'])
prefix=u.config['sql']['data_logger']['prefix']

class mon:
	def __init__(self,u,typ,name):
		self.u = u
		self.typ = typ
		self.name = u.config['amqp']['exchanges'][name]
		self.names = {}
		self.skips = set()
		self.f = 0

	async def start(self):
		await self.u.register_alert_async('#', self.callback, durable='log_mysql', call_conv=CC_MSG)

	async def _old_start(self):
		self.channel = (await u.conn.amqp.channel())
		await self.channel.exchange_declare(self.name, self.typ, passive=True)
		self.queue_name = 'mon_'+self.name+'_'+self.u.uuid
		self.queue = (await self.channel.queue_declare(self.queue_name, auto_delete=True, passive=False, exclusive=True))
		await self.channel.basic_qos(prefetch_count=1,prefetch_size=0,connection_global=False)
		await self.channel.queue_bind(self.queue_name, self.name, routing_key='#')
		await self.channel.basic_consume(queue_name=self.queue_name, callback=self.callback)
	
	#async def callback(self, channel,body,envelope,properties):
	async def callback(self, msg):
		try:
			body = msg.data
			#if properties.content_type == 'application/json' or properties.content_type.startswith('application/json+'):
			#	body = json.loads(body.decode('utf-8'))

			if isinstance(body,bytes):
				body = body.decode("utf-8")
			if not isinstance(body,dict):
				body = {'value':body, 'event':msg.routing_key.split('.')[2:]}
			dep = '?' if body.get('deprecated',False) else '.'
			try:
				nam = ' '.join(body['event'])
			except KeyError:
				#pprint.pprint(body)
				return

			done=False
			async with db() as d:
				for k in ('value','counter','state','temperature','humidity','average'):
					val = body.get(k,None)
					if val is None:
						continue
					aval=0
					if not isinstance(val,(dict,tuple,list)):
						try:
							val = float(val)
						except ValueError:
							if val.lower() in ('true','on','start'):
								val = 1
							elif val.lower() in ('false','off','done'):
								val = 0
							else:
								pprint.pprint(body)
								continue
					if k == "value":
						name = nam
					else:
						name = nam+' '+k
					if k == 'average':
						aval = float(body.get('turbulence',0))
					#print(dep,val,nam)
					try:
						tid = self.names[name]
					except KeyError:
						try:
							tid,mode,rate = await d.DoFn("select id,method,rate from %stype where tag=${name} for update"%(prefix,), name=name,)
						except NoData:
							tid = await d.Do("insert into %stype set tag=${name}"%(prefix,), name=name,)
							mode = None
							rate = 0
						if mode == 1:
							self.skips.add(name)
						tid = self.names[name] = [tid,rate,time()]

					else:
						if tid[2]+tid[1] > time():
							print("*",self.f,"\r", end="")
							self.f += 1
							sys.stdout.flush()
							continue
					tid[2] = time()
					if name in self.skips:
						await d.Do("update %stype set timestamp=from_unixtime(${ts}) where id=${tid}"%(prefix,), tid=tid[0], ts=msg.timestamp, _empty=True)
						self.f += 1
					else:
						self.f = await d.Do("insert into %slog set value=${value},aux_value=${aux_value},data_type=${tid},timestamp=from_unixtime(${ts})"%(prefix,), value=val,aux_value=aval,tid=tid[0], ts=msg.timestamp)
						await d.Do("update %stype set timestamp=from_unixtime(${ts}), n_values=n_values+1 where id=${tid}"%(prefix,), tid=tid[0], ts=msg.timestamp)
						#print(dep,val,name)
					print(" ",self.f,"\r", end="")
					sys.stdout.flush()
					done=True
			if not done:
				if not len(body['event']) or body['event'][0] not in {'wait','running','motion'} and nam != "motion test" and not nam.startswith("onewire scan") and not nam.startswith("fs20 unknown"):
					print(body)

		except Exception as exc:
			logger.exception("Problem processing %s", repr(body))
			quitting.set()

##################### main loop

loop=None
quitting=None

async def mainloop():
	await u.start()
	m = mon(u,'topic','alert')
	await m.start()
	await quitting.wait()
	await u.stop()

def _tilt():
	loop.remove_signal_handler(signal.SIGINT)
	loop.remove_signal_handler(signal.SIGTERM)
	quitting.set()

def main():
	global loop
	global quitting
	loop = asyncio.get_event_loop()
	quitting = asyncio.Event(loop=loop)
	loop.add_signal_handler(signal.SIGINT,_tilt)
	loop.add_signal_handler(signal.SIGTERM,_tilt)
	loop.run_until_complete(mainloop())

if __name__ == '__main__':
	main()


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
from sqlmix.async import Db,NoData

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

			dep = '?' if body.get('deprecated',False) else '.'
			try:
				nam = ' '.join(body['event'])
			except KeyError:
				#pprint.pprint(body)
				return

			done=False
			async with db() as d:
				for k in ('value','counter','state','temperature','humidity'):
					val = body.get(k,None)
					if val is None:
						continue
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
					#print(dep,val,nam)
					try:
						tid = self.names[name]
					except KeyError:
						try:
							tid, = await d.DoFn("select id from %stype where tag=${name}"%(prefix,), name=name,)
						except NoData:
							tid = await d.Do("insert into %stype set tag=${name}"%(prefix,), name=name,)
						self.names[name] = tid
					f = await d.Do("insert into %slog set value=${value},data_type=${tid},timestamp=from_unixtime(${ts})"%(prefix,), value=val,tid=tid, ts=msg.timestamp)
					#print(dep,val,name)
					print(" ",f,"\r", end="")
					sys.stdout.flush()
					done=True
			if not done:
				if body['event'][0] not in {'wait','running','motion'} and nam != "motion test" and not nam.startswith("onewire scan") and not nam.startswith("fs20 unknown"):
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


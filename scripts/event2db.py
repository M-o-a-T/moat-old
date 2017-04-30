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
from qbroker.unit import Unit, CC_DATA
from qbroker.util.tests import load_cfg
import signal
import pprint
import json
from sqlmix.async import Db,NoData

import logging
import sys
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

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

	async def start(self):
		self.channel = (await u.conn.amqp.channel())
		await self.channel.exchange_declare(self.name, self.typ, passive=True)
		self.queue_name = 'mon_'+self.name+'_'+self.u.uuid
		self.queue = (await self.channel.queue_declare(self.queue_name, auto_delete=True, passive=False, exclusive=True))
		await self.channel.basic_qos(prefetch_count=1,prefetch_size=0,connection_global=False)
		await self.channel.queue_bind(self.queue_name, self.name, routing_key='#')
		await self.channel.basic_consume(queue_name=self.queue_name, callback=self.callback)
	
	async def callback(self, channel,body,envelope,properties):
		if properties.content_type == 'application/json' or properties.content_type.startswith('application/json+'):
			body = json.loads(body.decode('utf-8'))

		m = {'body':body, 'prop':{}, 'env':{}}
		for p in dir(properties):
			if p.startswith('_'):
				continue
			v = getattr(properties,p)
			if v is not None:
				m['prop'][p] = v
		for p in dir(envelope):
			if p.startswith('_'):
				continue
			v = getattr(envelope,p)
			if v is not None:
				m['env'][p] = v
		#pprint.pprint(m)
		dep = '?' if body.get('deprecated',False) else '.'
		val = body.get('value_delta',body.get('value',None))
		try:
			nam = ' '.join(body['event'])
		except KeyError:
			pprint.print(body)
		else:
			#print(dep,val,nam)
			if val is not None:
				async with db() as d:
					try:
						tid, = await d.DoFn("select id from %stype where tag=${name}"%(prefix,), name=nam,)
					except NoData:
						tid = await d.Do("insert into %stype set tag=${name}"%(prefix,), name=nam,)
					f = await d.Do("insert into %slog set value=${value},data_type=${tid}"%(prefix,), value=val,tid=tid)
					print(dep,val,nam)



		await self.channel.basic_client_ack(delivery_tag = envelope.delivery_tag)

##################### main loop

loop=None
jobs=None
quitting=False

class StopMe:
	async def run(self):
		global quitting
		quitting = True

async def mainloop():
	await u.start()
	m = mon(u,'topic','alert')
	await m.start()
	while not quitting:
		j = (await jobs.get())
		await j.run()
	await u.stop()

def _tilt():
	loop.remove_signal_handler(signal.SIGINT)
	loop.remove_signal_handler(signal.SIGTERM)
	jobs.put(StopMe())

def main():
	global loop
	global jobs
	jobs = asyncio.Queue()
	loop = asyncio.get_event_loop()
	loop.add_signal_handler(signal.SIGINT,_tilt)
	loop.add_signal_handler(signal.SIGTERM,_tilt)
	loop.run_until_complete(mainloop())

if __name__ == '__main__':
	main()


#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division,absolute_import

from homevent import patch;patch()
import rpyc
import sys
from homevent.base import Name,flatten
from homevent.times import humandelta
from datetime import datetime
import signal
import os
import codecs
from gevent import spawn,signal
from signal import SIGINT,SIGTERM
from gevent.event import Event

sys.stdout = codecs.getwriter('utf8')(sys.stdout)

TESTING=os.environ.get("HOMEVENT_TEST",False)

import amqp
import json
from pprint import pprint

modes = "log,list,cmd".split(",")
from optparse import OptionParser
parser = OptionParser(conflict_handler="resolve")
parser.add_option("-h","--help","-?", action="help",
	help="print this help text")
parser.add_option("-s", "--server", dest="host", action="store",
	default="127.0.0.1", help="Server to connect to")
parser.add_option("-u", "--user", dest="user", action="store",
	default="test", help="User to connect as")
parser.add_option("-p", "--pass", dest="pw", action="store",
	default="test", help="Password to connect with")
parser.add_option("-v", "--vhost", dest="vhost", action="store",
	default="/test", help="Virtual host to connect at")
parser.add_option("-x", "--exchange", dest="exchange", action="store",
	default="homevent_event", help="Exchange to listen at")

(opts, args) = parser.parse_args()

def on_msg(msg):
	try:
		msg.body = json.loads(msg.body)
	except Exception:
		pass
	pprint(msg.__dict__)

conn = amqp.connection.Connection(host=opts.host, userid=opts.user, password=opts.pw, login_method='AMQPLAIN', login_response=None, virtual_host=opts.vhost)
chan = conn.channel()
res = chan.exchange_declare(exchange=opts.exchange, type='topic', auto_delete=False, passive=False)
res = chan.queue_declare(exclusive=True)
chan.queue_bind(exchange=opts.exchange, queue=res.queue, routing_key="#")
chan.basic_consume(callback=on_msg, queue=res.queue, no_ack=True)

def main(opts,args):
	sig = Event()

	def run():
		while not sig.isSet():
			conn.drain_events()

	def do_shutdown():
		sig.set()
	signal(SIGINT,do_shutdown)
	signal(SIGTERM,do_shutdown)

	j = spawn(run)
	sig.wait()
	j.kill()
	conn.close()

if __name__ == "__main__":
	try:
		main(opts,args)
	except Exception:
		raise
	except BaseException:
		pass


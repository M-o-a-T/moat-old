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
u.config['amqp']['exchanges']['alert'] = "moat.event"
cf=u.config['amqp']['server']
print(cf['host'],cf['virtualhost'])

class mon:
    def __init__(self,u,typ,name):
        self.u = u
        self.typ = typ
        self.name = u.config['amqp']['exchanges'][name]
        self.names = {}
        self.skips = set()
        self.f = 0

    async def start(self):
        await self.u.register_alert_async('#', self.callback, durable=False, call_conv=CC_MSG)

    #async def callback(self, channel,body,envelope,properties):
    async def callback(self, msg):
        try:
            dep = '_'
            body = msg.data
            nam = msg.routing_key
            if nam.startswith("hass."):
                if isinstance(body,bytes):
                    body = body.decode('utf-8')
                try:
                    body = json.loads(body)
                except Exception:
                    pass
            if isinstance(body,(str,bytes,int,float,list,tuple)):
                body = { 'raw': body, 'event':nam.split('.') }
            else:
                dep = '.'
            if True:
                body.pop("timestamp",None)
                body.pop("steps",None)
                body.pop("last_value",None)
                body.pop("data",None)

                if body.get('deprecated',False):
                    return
                try:
                    nam = body.pop("event")
                except KeyError:
                    if nam == "hass.event" and body.get('event_type','') == 'state_changed':
                        return
                else:
                    if nam is None:
                        pprint.pprint(body)
                        return
                    if nam[0] == "wait":
                        return
                    if len(nam) > 2 and nam[0] == 'hass' and nam[1] == 'state' and nam[-1] != 'state':
                        return
                    if len(nam) == 4 and nam[0] == "ets" and nam[1] == "meter" and nam[2] in {"EG","UG","OG"} and nam[3] in {"P","P1","P2","P3", "I","I1","I2","I3", "W","W1","W2","W3", "U1","U2","U3", "phi1","phi2","phi3", "VAr","VAr1","VAr2","VAr3"}:
                        return
                    if len(nam) == 5 and nam[0] == "monitor" and nam[1] == "update" and nam[2] == "temperatur" and nam[3] in {"aussen","heizung","wasser","unten"} and nam[4] in {"kessel","dach","pumpe","saeule","vorne","hinten","vorlauf","ruecklauf"}:
                        return
                    if len(nam) >= 3 and nam[0] == "monitor" and nam[1] == "update" and body.get('value_delta',-1) == 0:
                        return
                    nam = ' '.join(nam)
                if nam in {
                        "monitor update wind dir",
                        "monitor update wind speed",
                        "monitor update light",
                        }:
                    return
                if nam == "hass.event" and body.get('event_type','') == 'call_service':
                    ed = body['event_data']
                    if ed.get('domain','') == "mqtt" and ed.get('service','') == 'publish':
                        return

            print(dep,nam,body)
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


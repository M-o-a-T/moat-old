# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
## This file is part of devrun, a comprehensive controller and monitor for
## various typed code.
##
## devrun is Copyright © 2016 by Matthias Urlichs <matthias@urlichs.de>,
## it is licensed under the GPLv3. See the file `README.rst` for details,
## including optimistic statements by the author.
##
## This paragraph is auto-generated and may self-destruct at any time,
## courtesy of "make update". The original is in ‘utils/_boilerplate.py’.
## Thus, please do not remove the next line, or insert any blank lines.
##BP

import asyncio
import aiohttp
import jinja2
import os
import aiohttp_jinja2
from hamlish_jinja import HamlishExtension
from blinker import Signal
from functools import partial

from qbroker.unit import CC_DICT
import qbroker.codec.json_obj as json

import logging
logger = logging.getLogger(__name__)

from moat.web import WEBDATA_DIR,WEBDATA
from .app import BaseView,BaseExt

class ApiView(BaseView):
    path = '/api/control'
    view = None
    items = {}

    async def get(self):
        app = self.request.app
        sig = app.get('moat.update',None)
        cmd = app['moat.cmd']
        if sig is None:
            app['moat.update'] = sig = Signal()
#            await cmd.amqp.register_alert_async('update.charger',
#                partial(send_charger_update,sig),
#                call_conv=CC_DICT)
#        sig.connect(self.send_update)

        socks = app.setdefault('websock',set())
        logger.debug('starting')

        self.ws = aiohttp.web.WebSocketResponse()
        await self.ws.prepare(self.request)

        socks.add(self)
        logger.debug('open')
        self.job = asyncio.Task.current_task(cmd.loop)
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    logger.info("Msg %s",msg.data)
                    msg = json.decode(msg.data)
                    act = msg.get('action',"")
                    if act == "locate":
                        loc = msg.get('location','')
                        if not loc:
                            loc = cmd.app.rootpath
                        elif loc[0] == '#':
                            loc = loc[1:]
                        await self.set_location(loc)
                    else:
                        id = msg.get('id',None)
                        if id is None:
                            logger.warn("Unknown action: %s",repr(msg))
                        else:
                            try:
                                this = self.items[id]
                                this.recv_msg(act, view=self, **msg)
                            except KeyError:
                                logger.warn("Unknown ID: %s",repr(id))
                            except Exception as exc:
                                logger.exception("%s on %s:%s",act,id,this)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warn('ws connection closed: %s', ws.exception())
                    break
                else:
                    logger.info("Msg %s",msg)
        finally:
            socks.remove(self)
            #sig.disconnect(self.send_update)
            logger.debug('closed')
            self.job = None

        return self.ws

    async def send_field(self, t, level=1):
        await t.send_item(self, level=level)

    async def set_location(self, loc):
        try:
            cmd = self.request.app['moat.cmd']
            t = await cmd.root.tree.lookup(WEBDATA_DIR)
            t = await t.lookup(loc)
        except KeyError:
            self.send_json(action="error", msg="Location '%s' not found" % (loc,))
            return

        self.view = t
        await self.setup_dir(t)
        await self.send_dir(t, 0)

    async def setup_field(self,t):
        t = await t
        print(t)
        pass

    async def setup_dir(self,t):
        for k,v in t.items():
            print(k,v)
            if k[0] == ':':
                continue
            v = await v
            if WEBDATA in v:
                await self.setup_field(v[WEBDATA])
            else:
                await self.setup_dir(v)

    async def send_dir(self,t, level=0):
        try:
            await t.send_item(self, level=level)
        except Exception as exc:
            logger.exception(t)
            raise
        level += 1
        for k,v in t.items():
            if k[0] == ':':
                continue
            if WEBDATA in v:
                await self.send_field(v[WEBDATA],level)
            else:
                await self.send_dir(v,level)

    def send_json(self, this=None, **kw):
        if this is not None:
            self.items[kw[id]] = this
        try:
            self.ws.send_json(kw)
        except Exception:
            self.job.cancel()

#def send_charger_update(_sig, **kw):
#    kw['action'] = 'update'
#    kw['class'] = 'charger'
#    _sig.send(kw)


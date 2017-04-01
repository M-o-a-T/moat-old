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
from aiohttp import web
import jinja2
import os
import aiohttp_jinja2
from hamlish_jinja import HamlishExtension
from blinker import Signal
from qbroker.unit import CC_DICT
from functools import partial

import logging
logger = logging.getLogger(__name__)

from .app import BaseView,BaseExt

class ApiView(BaseView):
    path = '/api/control'
    async def get(self):
        app = self.request.app
        sig = app.get('moat.evc.update',None)
        cmd = app['moat.cmd']
        if sig is None:
            app['moat.evc.update'] = sig = Signal()
#            await cmd.amqp.register_alert_async('update.charger',
#                partial(send_charger_update,sig),
#                call_conv=CC_DICT)
        sig.connect(self.send_update)

        socks = app.setdefault('websock',set())
        logger.debug('starting')

        self.ws = web.WebSocketResponse()
        await self.ws.prepare(self.request)

        socks.add(self)
        logger.debug('open')
        self.job = asyncio.Task.current_task(cmd.loop)
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warn('ws connection closed: %s', ws.exception())
                    break
        finally:
            socks.remove(self)
            sig.disconnect(self.send_update)
            logger.debug('closed')
            self.job = None

        return self.ws

    def send_update(self, kw):
        try:
            self.ws.send_json(kw)
        except Exception:
            self.job.cancel()

def send_charger_update(_sig, **kw):
    kw['action'] = 'update'
    kw['class'] = 'charger'
    _sig.send(kw)


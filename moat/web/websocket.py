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
import os
from blinker import Signal
from functools import partial

from qbroker.unit import CC_DICT
import qbroker.codec.json_obj as json

import logging
logger = logging.getLogger(__name__)

from moat.web import WEBDATA_DIR,WEBDATA
from .app import BaseView,BaseExt
from moat.util import do_async

class ApiView(BaseView):
    path = '/api/control'
    top_item = None

    def __init__(self,*a,**k):
        self.items = {}
        self.values = {}
        super().__init__(*a,**k)

    async def get(self):
        app = self.request.app
        sig = app.get('moat.update',None)
        srv = app['moat.server']
        if sig is None:
            app['moat.update'] = sig = Signal()
#            await srv.amqp.register_alert_async('update.charger',
#                partial(send_charger_update,sig),
#                call_conv=CC_DICT)
#        sig.connect(self.send_update)

        #socks = app.setdefault('websock',set())
        logger.debug('starting')

        self.ws = aiohttp.web.WebSocketResponse()
        await self.ws.prepare(self.request)

        #socks.add(self)
        logger.debug('open')
        self.job = asyncio.Task.current_task(srv.loop)
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    logger.debug("WebSocket: recv %s",msg.data)
                    msg = json.decode(msg.data)
                    act = msg.get('action',"")
                    if act == "locate":
                        loc = msg.get('location','')
                        if not loc:
                            loc = srv.app.rootpath
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
                                break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warn('ws connection closed: %s', ws.exception())
                    break
                else:
                    logger.info("Msg %s",msg)
        finally:
            #socks.remove(self)
            #sig.disconnect(self.send_update)
            logger.debug('closed')
            self.job = None
            await self.ws.close()
            pass

        return self.ws

    async def set_location(self, loc):
        try:
            srv = self.request.app['moat.server']
            t = await srv.tree.lookup(WEBDATA_DIR)
            t = await t.lookup(loc)
        except KeyError:
            self.send_json(action="error", msg="Location '%s' not found" % (loc,))
            return

        self.items = {}
        self.top_item = t
        await t.feed_subdir(self)

    def key_for(self, item):
        """\
            create and return a unique key for an item.

            We can't use the create ID because while etcd_tree creates
            directories one at a time, other utilities may not bother.
            """
        if item is self.top_item:
            return "content"
        # return "f_"+str(item._cseq) # debug only
        seq = getattr(item,'web_id',None)
        if seq is None:
            srv = self.request.app['moat.server']
            item.web_id = seq = srv.next_web_id
            srv.next_web_id = seq+1
        return "f_"+str(seq)

    async def add_item(self, item,level, **kw):
        try:
            key = self.key_for(item)
            if key not in self.items:
                self.items[key] = (item,level)
                u = getattr(item,'updates',None)
                if u is not None:
                    u.connect(self.queue_update)
                await item.send_insert(self, level=level, **kw)
            else:
                logger.debug("Repeat add %s",item)
                await item.send_update(self, level=level, **kw)
        except Exception as e:
            logger.exception("Adding %s",item)
            if self.job is not None:
                self.job.cancel()
            self.send_json(action="error",msg="update "+str(item))

    def get_level(self,this):
        """Check if the element is new"""
        key = self.key_for(this)
        return self.items[key][1]

    async def send_update(self, item,level, **kw):
        try:
            key = self.key_for(item)
            await item.send_update(self,level=level, **kw)
        except Exception as e:
            logger.exception("updating %s",item)
            if self.job is not None:
                self.job.cancel()
            self.send_json(action="error",msg="update "+str(item))

    async def send_delete(self, item,level, **kw):
        try:
            await item.send_delete(self,level=level)
        except Exception as e:
            logger.exception("deleting %s",item)
            if self.job is not None:
                self.job.cancel()
            self.send_json(action="error",msg="update "+str(item))

    def queue_update(self,item,**kw):
        key = self.key_for(item)
        try:
            _,level = self.items[key]
        except KeyError:
            par = self.key_for(item.parent)
            try:
                _,level = self.items[par]
            except KeyError:
                logger.debug("Parent not here: %s",item)
                return
            else:
                do_async(self.add_item,item,level=level+1, **kw)
        else:
            if item.is_new is None:
                do_async(self.send_delete,item,level=level, **kw)
            else:
                do_async(self.send_update,item,level=level, **kw)

    def send_json(self, **kw):
        if self.job is None:
            return
        if self.ws.closed:
            self.job.cancel()
            return
        try:
            self.ws.send_json(kw)
        except Exception as exc:
            logger.exception("Xmit %s",kw)
            if self.job is not None:
                self.job.cancel()

#def send_charger_update(_sig, **kw):
#    kw['action'] = 'update'
#    kw['class'] = 'charger'
#    _sig.send(kw)


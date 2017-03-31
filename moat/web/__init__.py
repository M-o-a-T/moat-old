# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
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

from aiohttp import web

from moat.script.util import objects

import logging
logger = logging.getLogger(__name__)

async def hello(request):
    return web.Response(text="This is MoaT. You did not set up a handler for the root view.")

class BaseView(web.View):
    path = None

class BaseExt:
    @classmethod
    async def start(cls, app):
        pass
    @classmethod
    async def stop(cls, app):
        pass

class FakeReq:
    """A very hacky way to test whether a resource exists on a path"""
    def __init__(self, path):
        self.__path = path
    @property
    def method(self):
        return 'GET'
    @property
    def rel_url(self):
        class _FR:
            @property
            def raw_path(s):
                return self._FakeReq__path
        return _FR()

class App:
    srv=None
    app=None
    handler=None

    def __init__(self, cmd):
        self.loop = cmd.loop
        self.app = web.Application(loop=self.loop)
        self.app['moat.cmd'] = cmd

    async def start(self, bindto,port):
        for cls in objects('moat.web', BaseExt):
            await cls.start(self.app)
        for view in objects("moat.web",BaseView):
            if view.path is not None:
                print(view)
                self.app.router.add_route('*', view.path, view)

        r = FakeReq('/')
        r = await self.app.router.resolve(r)
        if getattr(r,'_exception',None) is not None:
            self.app.router.add_get('/', hello)

        self.handler = self.app.make_handler()
        self.srv = await self.loop.create_server(self.handler, bindto,port)
        logger.debug('serving on %s', self.srv.sockets[0].getsockname())

    async def stop(self):
        if self.srv is not None:
            self.srv.close()
            await self.srv.wait_closed()
        if self.app is not None:
            for cls in objects('moat.web', BaseExt):
                await cls.stop(self.app)
            await self.app.shutdown()
        if self.handler is not None:
            await self.handler.finish_connections(60.0)
        if self.app is not None:
            await self.app.cleanup()


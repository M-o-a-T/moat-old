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
import jinja2
import os
import aiohttp_jinja2
from hamlish_jinja import HamlishExtension

from .app import BaseView,BaseExt

class JinjaExt(BaseExt):
    @classmethod
    async def start(self,app):
        env = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),'templates')), extensions=[HamlishExtension])
        env.hamlish_file_extensions=('.haml',)
        env.hamlish_mode='debug'
        env.hamlish_enable_div_shortcut=True

        app.router.add_static('/static', os.path.join(os.path.dirname(__file__),'static'), name='static')
        env.filters['static'] = lambda x:app.router.named_resources()['static'].url_for(filename=x)

class RootView(BaseView):
    path = '/'
    @aiohttp_jinja2.template('main.haml')
    async def get(self):
        ##qb = self.request.app['moat.cmd'].amqp
        #x = await qb.rpc('info', _cmd='state',_subsys='charger')
        return {'foo':'bar', 'host':self.request.headers['host']}


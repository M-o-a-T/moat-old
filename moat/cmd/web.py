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

"""Run a web service"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import types
import inspect
from aiohttp import web
from traceback import print_exc
from collections.abc import Mapping

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK
from moat.web import App

import logging
logger = logging.getLogger(__name__)

__all__ = ['WebCommand']

class WebCommand(Command):
    name = "web"
    usage = "-b BINDTO -p PORT -r WEB"
    summary = "Run a web server"
    description = """\
This command runs a web server with the data at /web (by default).
"""

    # process in order

    def addOptions(self):
        self.parser.add_option('-r','--root',
            action="store", dest="root",
            help="run a web server (default: /web)")
        self.parser.add_option('-b','--bind-to',
            action="store", dest="host",
            help="address to bind to", default="0.0.0.0")
        self.parser.add_option('-p','--port',
            action="store", dest="port", type=int,
            help="port to use", default=59980)

# server/host and /port: bind address and port to use
# /root/…/:dir : optional: addiional data for this subdirectory
# /root/…/:item : one thing to display

    def handleOptions(self):
        self.rootpath = self.options.root
        self.host = self.options.host
        self.port = self.options.port

    async def do(self,args):
        if args:
            raise CommandError("this command takes no arguments")

        self.loop = self.root.loop
        self.app = App(self)
        await self.app.start(self.host,self.port)

        # now serving
        while True:
            await asyncio.sleep(9999,loop=self.loop)


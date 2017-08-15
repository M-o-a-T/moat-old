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
import inspect
from aiohttp import web
from traceback import print_exc
from yaml import dump

from moat.script import Command, SubCommand, CommandError
from moat.web import WEBDEF_DIR,WEBDEF, WEBDATA_DIR,WEBDATA, webdefs, WEBCONFIG
from moat.web.base import WebdefDir, DefaultConfig
from moat.util import r_dict, r_show
from moat.cmd.task import _ParamCommand

import logging
logger = logging.getLogger(__name__)

__all__ = ['WebCommand']

class DefSetup:
    async def setup(self, meta=False):
        await super().setup()
        tree = await self.root._get_tree()
        if meta:
            t = await tree.subdir(WEBDEF_DIR)
        else:
            t = await tree.subdir(WEBDATA_DIR)
        return t

class DefInitCommand(DefSetup,Command):
    name = "init"
    summary = "Set up web definitions"
    description = """\
Web definitions are stored in etcd at /meta/web/**/:def.

This command sets up that data. If you mention module or class names
on the command line, they are added, otherwise everything under
'moat.web.*' is used.

"""

    def addOptions(self):
        self.parser.add_option('-f','--force',
            action="store_true", dest="force",
            help="update existing values")

    def handleOptions(self):
        self.force = self.options.force

    async def do(self,args):
        tree = await self.root._get_tree()
        t = await self.setup(meta=True)
        if args:
            objs = []
            for a in args:
                m = import_string(a)
                if isinstance(m,types.ModuleType):
                    from moat.script.util import objects
                    n = 0
                    for c in objects(m, WebdefDir, filter=lambda x:getattr(x,'name',None) is not None):
                        await t.add_webdef(c, force=self.force)
                        n += 1
                    if self.root.verbose > (1 if n else 0):
                        print("%s: %s webdef%s found." % (a,n if n else "no", "" if n==1 else "s"), file=self.stdout)
                else:
                    if not isinstance(m,WebdefDir):
                        raise CommandError("%s is not a web definition"%a)
                    await t.add_webdef(m, force=self.force)
        else:
            for c in webdefs():
                await t.add_webdef(c, force=self.force)

        await t.wait()

class DefListCommand(DefSetup,Command):
    name = "list"
    summary = "List web definitions"
    description = """\
Web definitions are stored in etcd at /meta/web/**/:def.

This command shows that data. If you mention a definition's name,
details are shown in YAML format, else a short list of names is shown.
"""

    def addOptions(self):
        self.parser.add_option('-a','--all',
            action="store_true", dest="all",
            help="show details for all entries")

    async def do(self,args):
        t = await self.setup(meta=True)
        if args:
            if self.options.all:
                raise CommandError("Arguments and '-a' are mutually exclusive")
            dirs = []
            for a in args:
                dirs.append(await t.subdir(a, create=False))
            verbose = True
        else:
            dirs = [t]
            verbose = self.options.all
        for tt in dirs:
            async for web in tt.tagged(WEBDEF):
                path = web.path[len(WEBDEF_DIR):-1]
                if verbose:
                    dump({path: r_dict(dict(web))}, stream=self.stdout)
                else:
                    print('/'.join(path),web.get('summary',web.get('descr','??')), sep='\t',file=self.stdout)

class DefDeleteCommand(DefSetup,Command):
    name = "delete"
    summary = "Delete web definitions"
    description = """\
Web definitions are stored in etcd at /meta/web/**/:def.

This command deletes (some of) that data.
"""

    def addOptions(self):
        self.parser.add_option('-f','--force',
            action="store_true", dest="force",
            help="not forcing won't do anything")

    async def do(self,args):
        td = await self.setup(meta=True)
        if not args:
            if not cmd.root.cfg['testing']:
                raise CommandError("You can't delete everything.")
            args = td.tagged(WEBDEF)
        for k in args:
            t = await td.subdir(k,name=WEBDEF, create=False)
            if self.root.verbose:
                print("%s: deleted"%k, file=self.stdout)
            rec = True
            while True:
                p = t._parent
                if p is None: break
                p = p()
                if p is None or p is t: break
                try:
                    await t.delete(recursive=rec)
                except etcd.EtcdDirNotEmpty:
                    if rec:
                        raise
                    break
                rec = False
                t = p

class DefParamCommand(_ParamCommand):
    _def = True
    DIR=WEBDEF_DIR
    TAG=WEBDEF
    summary = "Parameterize web definitions"
    description = """\
Web definitions are stored in etcd at /meta/web/**/:def.
""" + _ParamCommand.description

class ParamCommand(_ParamCommand):
    _def = False
    DIR=WEBDATA_DIR
    TAG=WEBDATA
    summary = "Parameterize web entries"
    description = """\
Web entries are stored in etcd at /web/**/:item.
""" + _ParamCommand.description

class _DefAddUpdate:
    """Mix-in to add or update a web entry (too much)"""

    async def do(self,args):
        t = await self.setup(meta=True)

        try:
            data = {}
            name=""

            webpath = args[0].rstrip('/').lstrip('/')
            if webpath == "":
                raise CommandError("Empty web entry path?")
            if webpath.endswith(WEBDATA):
                raise CommandError("Don't add the tag")

            if not self._update:
                if '/' not in webpath:
                    raise CommandError("You can't add a top-level web definition")
                parent = webpath[:webpath.rindex('/')]
                try:
                    await t.subdir(parent,name=WEBDEF, create=False)
                except KeyError:
                    raise CommandError("The web definition '%s' does not exist" % (parent))

            p=1
            while p < len(args):
                try:
                    k,v = args[p].split('=')
                except ValueError:
                    break
                p += 1
                data[k] = v
            descr = " ".join(args[p:])
        except IndexError:
            raise CommandError("Missing command parameters")
        finally:
            pass

        try:
            web = await t.subdir(webpath, name=WEBDEF, create=not self._update)
        except KeyError:
            raise CommandError("Web item '%s' not found." % webpath)
        if descr:
            await web.set('descr', descr, sync=False)
        if data:
            for k,v in data.items():
                if v == "":
                    try:
                        await web.delete(k, sync=False)
                    except KeyError:
                        pass
                else:
                    await web.set(k,v, sync=False)
            

class DefAddCommand(_DefAddUpdate,DefSetup,Command):
    name = "add"
    summary = "add a derived web definition"
    description = """\
Create a new derived web definition.

Arguments:

* the new web definition's path (must not exist, but its parent is required)

* data=value parameters (entry-specific, optional)

* a descriptive name (not optional)

"""
    _update = False
class DefUpdateCommand(_DefAddUpdate,DefSetup,Command):
    name = "change"
    summary = "change a web definition"
    description = """\
Update a web entry.

Arguments:

* the web definition's path (required)

* data=value entries (deletes the key if value is empty)

* a descriptive name (optional, to update)

"""
    _update = True

class DefCommand(SubCommand):
    subCommandClasses = [
        DefInitCommand,
        DefListCommand,
        DefAddCommand,
        DefUpdateCommand,
        DefDeleteCommand,
        DefParamCommand,
    ]
    name = "def"
    summary = "Manage web definitios"
    description = """\
Commands to set up and admin the web definitions known to MoaT.
"""

class ServeCommand(DefSetup,Command):
    name = "serve"
    usage = "-b BINDTO -p PORT -r WEB"
    summary = "Run a web server"
    description = """\
This command runs a web server with the data at /web (by default).
"""

    def addOptions(self):
        self.parser.add_option('-b','--bind-to',
            action="store", dest="host",
            help="address to bind to", default="0.0.0.0")
        self.parser.add_option('-p','--port',
            action="store", dest="port", type=int,
            help="port to use", default=59980)
        self.parser.add_option('-r','--root',
            action="store", dest="root",
            help="subtree to use by default", default="default")

# server/host and /port: bind address and port to use
# /root/…/:dir : optional: addiional data for this subdirectory
# /root/…/:item : one thing to display

    def handleOptions(self):
        super().handleOptions()
        self.host = self.options.host
        self.port = self.options.port
        self.rootpath = self.options.root

    async def do(self,args):
        if args:
            raise CommandError("this command takes no arguments")

        from moat.web.app import App
        self.loop = self.root.loop
        self.app = App(self)
        self.app.tree = await self.root._get_tree()
        await self.app.start(self.host,self.port, self.rootpath)

        # now serving
        while True:
            await asyncio.sleep(9999,loop=self.loop)

class ListCommand(DefSetup,Command):
    name = "list"
    summary = "List web entries"
    description = """\
Web entries are stored in etcd at /web/**/:item.

This command shows that data. Depending on verbosity, output is
a one-line summary, human-readable detailed state, or details as YAML.
"""

    def addOptions(self):
        self.parser.add_option('-t','--this',
            action="count", dest="this", default=0,
            help="Show the given job only (-tt for jobs one level below, etc.)")

    async def do(self,args):
        t = await self.setup()
        if args:
            dirs = []
            for a in args:
                try:
                    dirs.append(await t.subdir(a, create=False))
                except KeyError:
                    raise CommandError("'%s' does not exist"%(a,))
        else:
            dirs = [t]
        for tt in dirs:
            async for web in tt.tagged(WEBDATA, depth=self.options.this):
                path = web.path[len(WEBDATA_DIR):-1]
                if self.root.verbose == 2:
                    print('*','/'.join(path), sep='\t',file=self.stdout)
                    for k,v in r_show(web,''):
                        print(k,v, sep='\t',file=self.stdout)

                elif self.root.verbose > 1:
                    dump({'/'.join(path):r_dict(dict(web))}, stream=self.stdout)
                else:
                    path = '/'.join(path)
                    name = web.get('name','-')
                    if name == path:
                        name = "-"
                    print(path,name,web.get('descr','-'), sep='\t',file=self.stdout)


class _AddUpdate:
    """Mix-in to add or update a web entry (too much)"""

    async def do(self,args):
        try:
            data = {}
            webdefpath=""
            name=""
            p=0

            webpath = args[p].rstrip('/').lstrip('/')
            if webpath == "":
                raise CommandError("Empty web entry path?")
            if webpath.endswith(WEBDATA):
                raise CommandError("Don't add the tag")
            p+=1

            if not self._update:
                webdefpath = args[p].rstrip('/').lstrip('/')
                if webdefpath == "":
                    raise CommandError("Empty web definition path?")
                if webdefpath.endswith(WEBDEF):
                    raise CommandError("Don't add the tag")
                p+=1
            while p < len(args):
                try:
                    k,v = args[p].split('=')
                except ValueError:
                    break
                p += 1
                if k == "name":
                    name = v
                else:
                    data[k] = v
            if not self._update:
                args[p] # raises IndexError if nothing is left
            descr = " ".join(args[p:])
        except IndexError:
            raise CommandError("Missing command parameters")
        t = await self.setup(meta=False)
        if not self._update:
            try:
                td = await self.setup(meta=True)
                webdef = await td.subdir(webdefpath,name=WEBDEF, create=False)
            except KeyError:
                raise CommandError("Web def '%s' not found" % webdefpath)

        try:
            web = await t.subdir(webpath,name=WEBDATA, create=not self._update)
        except KeyError:
            raise CommandError("Web item '%s' not found." % webpath)
        if not self._update:
            await web.set('def', webdefpath, sync=False)
        if name:
            await web.set('name', name, sync=False)
        if descr:
            await web.set('descr', descr, sync=False)
        if data:
            for k,v in data.items():
                if v == "":
                    try:
                        await web.delete(k, sync=False)
                    except KeyError:
                        pass
                else:
                    await web.set(k,v, sync=False)
            

class AddCommand(_AddUpdate,DefSetup,Command):
    name = "add"
    summary = "add a web entry"
    description = """\
Create a new web entry.

Arguments:

* the new web entry's path (must not exist)

* the web entry definition's path (must exist)

* data=value parameters (entry-specific, optional)

* a descriptive name (not optional)

"""
    _update = False
class UpdateCommand(_AddUpdate,DefSetup,Command):
    name = "change"
    summary = "change a web entry"
    description = """\
Update a web entry.

Arguments:

* the web entry's path (required)

* data=value entries (deletes the key if value is empty)

* a descriptive name (optional, to update)

"""
    _update = True

class DeleteCommand(DefSetup,Command):
    name = "delete"
    summary = "Delete a web entry"
    description = """\
Web entries are stored in etcd at /web/**/:item.

This command deletes one of these entries.
"""

    def addOptions(self):
        self.parser.add_option('-f','--force',
            action="store_true", dest="force",
            help="not forcing won't do anything")

    async def do(self,args):
        t = await self.setup(meta=False)
        if not args:
            if not cmd.root.cfg['testing']:
                raise CommandError("You can't delete everything.")
            args = t
        for k in args:
            try:
                web = await t.subdir(k,name=WEBDATA, create=False)
            except KeyError:
                raise CommandError("%s: does not exist"%k)
            if self.root.verbose:
                print("%s: deleted"%k, file=self.stdout)
            rec = True
            while True:
                p = web._parent
                if p is None: break
                p = p()
                if p is None: break
                if p is web: break
                try:
                    await web.delete(recursive=rec)
                except etcd.EtcdDirNotEmpty:
                    if rec:
                        raise
                    break
                rec = False
                web = p

class ConfigCommand(_ParamCommand):
    _def = False
    _make = True
    name = "config"
    _VARS = set(DefaultConfig.keys())
    DIR=WEBDATA_DIR
    TAG=WEBCONFIG
    summary = "Configure display"
    description = """\
Web display parameters are stored in etcd at /web/**/:config.
""" + _ParamCommand.description


class WebCommand(SubCommand):
        name = "web"
        summary = "Configure the web frontend"
        description = """\
Commands to configure, and run, a basic web front-end.
"""

        # process in order
        subCommandClasses = [
                DefCommand,
                ListCommand,
                AddCommand,
                ParamCommand,
                ConfigCommand,
                UpdateCommand,
                DeleteCommand,
                ServeCommand,
        ]


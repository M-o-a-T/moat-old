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

"""Manage infrastructure description in MoaT"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import inspect
from traceback import print_exc
from yaml import dump

from moat.script import Command, SubCommand, CommandError
from moat.infra import INFRA_DIR, INFRA
from moat.util import r_dict, r_show
from moat.cmd.task import _ParamCommand,DefSetup

import logging
logger = logging.getLogger(__name__)

__all__ = ['InfraCommand']

class ListCommand(DefSetup,Command):
    DIR = INFRA_DIR
    name = "list"
    summary = "List infrastructure entries"
    description = """\
Infrastructure entries are stored in etcd at /infra/**/:host.
The path reflects the host's (reversed) domain name.

This command shows that data. Depending on verbosity, output is
a one-line summary, human-readable detailed state, or details as YAML.
"""

    def addOptions(self):
        self.parser.add_option('-t','--this',
            action="count", dest="this", default=0,
            help="Show the given job only (-tt for jobs one level below, etc.)")
        self.parser.add_option('-n','--no-link',
            action="store_true", dest="nolink",
            help="only show hosts with no remote links")

    async def do(self,args):
        t = await self.setup()
        if args:
            dirs = []
            for a in args:
                a = reversed(a.split('.'))
                try:
                    dirs.append(await t.lookup(a))
                except KeyError:
                    raise CommandError("'%s' does not exist"%(a,))
        else:
            dirs = [t]
        for tt in dirs:
            async for item in tt.tagged(INFRA, depth=self.options.this):
                path = item.path[len(INFRA_DIR):-1]
                if self.options.nolink:
                    n = 0
                    try:
                        for h in item['ports'].values():
                            await h.remote
                            n += 1
                    except KeyError:
                        pass
                    if n:
                        continue
                if self.root.verbose == 2:
                    print('*','.'.join(path[::-1]), sep='\t',file=self.stdout)
                    for k,v in r_show(item,''):
                        print(k,v, sep='\t',file=self.stdout)

                elif self.root.verbose > 1:
                    dump({'.'.join(path[::-1]):r_dict(dict(item))}, stream=self.stdout)
                else:
                    path = '.'.join(path[::-1])
                    name = item.get('name','-')
                    if name == path:
                        name = "-"
                    print(path,name,item.get('descr','-'), sep='\t',file=self.stdout)


class _AddUpdate:
    """Mix-in to add or update an infrastructure entry (too much)"""
    DIR = INFRA_DIR

    async def do(self,args):
        try:
            data = {}
            name=""
            p=0

            path = '/'.join(args[p].split('.')[::-1])
            if path == "":
                raise CommandError("Empty domain name?")
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
        t = await self.setup()

        try:
            item = await t.subdir(path,name=INFRA, create=not self._update)
        except KeyError:
            raise CommandError("Infrastructure item '%s' not found." % path)
        if name:
            await item.set('name', name, sync=False)
        if descr:
            await item.set('descr', descr, sync=False)
        if data:
            for k,v in data.items():
                if v == "":
                    try:
                        await item.delete(k, sync=False)
                    except KeyError:
                        pass
                else:
                    await item.set(k,v, sync=False)
            

class AddCommand(_AddUpdate,DefSetup,Command):
    name = "add"
    summary = "add an infrastructure entry"
    description = """\
Create a new infrastructure entry.

Arguments:

* the new entry's DNS name (must not exist)

* data=value parameters (optional)

* a descriptive name (not optional)

"""
    _update = False

class UpdateCommand(_AddUpdate,DefSetup,Command):
    name = "change"
    summary = "change an infrastructure entry"
    description = """\
Update an infrastructure entry.

Arguments:

* the entry name (required)

* data=value entries (deletes the key if value is empty)

* an updated descriptive name (optional)

"""
    _update = True

class DeleteCommand(DefSetup,Command):
    DIR = INFRA_DIR
    name = "delete"
    summary = "Delete an infrastructure entry"
    description = """\
Infrastructure entries are stored in etcd at /infra/**/:host.

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
            path = tuple(k.split('.'))[::-1]
            try:
                tt = await t.subdir(path,name=INFRA, create=False)
            except KeyError:
                raise CommandError("%s: does not exist"%(path,))
            if self.root.verbose:
                print("%s: deleted"%k, file=self.stdout)
            rec=None
            while True:
                p = tt._parent
                if p is None: break
                p = p()
                if p is None: break
                if p is t: break
                try:
                    await tt.delete(recursive=rec)
                except etcd.EtcdDirNotEmpty:
                    break
                rec=False
                tt = p

class PortCommand(DefSetup,Command):
    DIR = INFRA_DIR
    name = "port"
    summary = "Configure a port of an infrastructure item"
    description = """\
Infrastructure parameters are stored in etcd at /infra/**/:host/port/NAME.

Usage: … port HOST NAME key=value… -- set
       … port HOST NAME            -- show one port
       … port HOST                 -- list all ports
       … port -d HOST NAME…        -- delete this port
       … port -d HOST *            -- delete all ports
"""

    def addOptions(self):
        self.parser.add_option('-d','--delete',
            action="store_true", dest="delete",
            help="delete a port")

    async def do(self, args):
        t = await self.setup()
        if not args:
            raise SyntaxError("You need to specify a host!")
        try:
            h = await t.lookup(reversed(args[0].split('.')), name=INFRA)
            h = await h.subdir('ports')
        except KeyError:
            print("Host '%s' is not known" % (args[0],), file=sys.stderr)
            return
        args = args[1:]
        if self.options.delete:
            if len(args) == 0:
                raise SyntaxError("You need to specify which ports to delete.") 
            if len(args) == 1 and args[0] == '*':
                args = list(h.keys())
            for p in args:
                await h.delete(p)
            return

        if not args:
            for k,v in r_show(h,''):
                print(k,v, sep='\t',file=self.stdout)
            return
        h = await h.subdir(args[0])
        args = args[1:]
        if not args:
            for k,v in r_show(h,''):
                print(k,v, sep='\t',file=self.stdout)
            return
        for a in args:
            try:
                k,v = a.split('=',1)
            except ValueError:
                print(h[a])
            else:
                if v == '':
                    await h.delete(k)
                else:
                    await h.set(k,v)

class LinkCommand(DefSetup,Command):
    DIR = INFRA_DIR
    name = "link"
    summary = "Link two infrastructure items"
    description = """\
Link two devices.

Usage: … link HOST_A PORT_A HOST_B PORT_B -- join
       … link HOST PORT                   -- show
       … link HOST                        -- show all
       … link -d HOST PORT                -- remove

Links are bidirectional.
"""

    def addOptions(self):
        self.parser.add_option('-d','--delete',
            action="store_true", dest="delete",
            help="delete a link")
        self.parser.add_option('-m','--missing',
            action="store_true", dest="missing",
            help="only show links with missing remote ports")

    async def do(self, args):
        t = await self.setup()
        if self.options.delete:
            if self.options.missing:
                raise SyntaxError("'-d' and '-m' cannot be used at the same time.")
            if len(args) != 2:
                raise SyntaxError("You need to specify which host+port to delete.") 
        else:
            if len(args) < 1:
                async for h in t.tagged(INFRA):
                    h = await h
                    try:
                        x = h['ports'].values()
                    except KeyError:
                        pass
                    else:
                        for p in x:
                            try:
                                r = await p.remote
                            except KeyError:
                                try:
                                    rh = p['host']
                                except KeyError:
                                    pass
                                else:
                                    print(h.dnsname,p.name,rh)
                            else:
                                if not self.options.missing:
                                    print(h.dnsname,p.name,r.host.dnsname,r.name)
                return
            elif len(args) == 1:
                h = await t.host(args[0],create=False)
                try:
                    x = h['ports'].values()
                except KeyError:
                    pass
                else:
                    for p in h['ports'].values():
                        try:
                            r = await p.remote
                        except KeyError:
                            try:
                                rh = p['host']
                            except KeyError:
                                pass
                            else:
                                print(p.name,rh)
                        else:
                            if not self.options.missing:
                                print(p.name,r.host.dnsname,r.name)
                return
            elif len(args) == 2:
                h = await t.host(args[0],create=False)
                p = h['ports'][args[1]]
                try:
                    r = await p.remote
                except KeyError:
                    try:
                        rh = p['host']
                    except KeyError:
                        pass
                    else:
                        print(rh)

                else:
                    print(r.host.dnsname,r.name)
                return
            elif len(args) > 4:
                raise SyntaxError("You need to specify host+port of both sides.") 
            elif self.options.missing:
                raise SyntaxError("'-m' can only be used when listing.")
        p1 = await t.host(args[0], create=False)
        p1 = await p1.subdir('ports',args[1])
        if self.options.delete:
            await p1.unlink()
        else:
            p2 = await t.host(args[2], create=False)
            if len(args) == 4:
                p2 = await p2.subdir('ports',args[3])
            await p1.link(p2)

class InfraCommand(SubCommand):
        name = "infra"
        summary = "Document your network infrastructure"
        description = """\
Commands to configure your network connectivity
"""

        # process in order
        subCommandClasses = [
                ListCommand,
                AddCommand,
                PortCommand,
                LinkCommand,
                UpdateCommand,
                DeleteCommand,
        ]


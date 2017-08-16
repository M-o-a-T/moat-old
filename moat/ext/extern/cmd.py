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

"""Run a dev service"""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import inspect
from yaml import dump

from moat.script import Command, SubCommand, CommandError
from moat.dev import DEV_DIR, DEV
from moat.util import r_dict, r_show
from moat.types import TYPEDEF_DIR, TYPEDEF
from .dev import ExternDevice

import logging
logger = logging.getLogger(__name__)

__all__ = ['DeviceCommand']

class DefSetup:
    """Mix-in for getting the root of my tree"""
    async def setup(self):
        path = DEV_DIR+(ExternDevice.prefix,)
        await self.root.setup(self)
        tree = self.root.tree
        t = await tree.subdir(path)
        return t

class ListCommand(DefSetup,Command):
    name = "list"
    summary = "List external devices"
    description = """\
External devices are stored in etcd at /dev/extern/**/:dev.

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
            async for dev in tt.tagged(DEV, depth=self.options.this):
                path = dev.path[len(DEV_DIR):-1]
                if self.root.verbose == 2:
                    print('*','/'.join(path), sep='\t',file=self.stdout)
                    for k,v in r_show(dev,''):
                        print(k,v, sep='\t',file=self.stdout)

                elif self.root.verbose > 1:
                    dump({'/'.join(path):r_dict(dict(dev))}, stream=self.stdout)
                else:
                    path = '/'.join(path)
                    name = dev.get('name','-')
                    val = dev.get('value','-')
                    if name == path:
                        name = "-"
                    print(path,name,val, sep='\t',file=self.stdout)


class _AddUpdate(DefSetup):
    """Mix-in to add or update a dev entry (too much)"""

    async def do(self,args):
        try:
            data = {}
            name=""
            p=0

            devpath = args[p].rstrip('/').lstrip('/')
            if devpath == "":
                raise CommandError("Empty dev entry path?")
            if devpath.endswith(DEV):
                raise CommandError("Don't add the tag")
            p+=1

            if not self._update:
                typepath = args[p].rstrip('/').lstrip('/')
                if typepath == "":
                    raise CommandError("Empty type path?")
                if typepath.endswith(TYPEDEF):
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
        t = await self.setup()
        if not self._update:
            try:
                td = await t.root.lookup(TYPEDEF_DIR)
                td = await td.lookup(typepath, name=TYPEDEF)
            except KeyError:
                raise CommandError("type '%s' not found" % (typepath,))

        try:
            dev = await t.subdir(devpath,name=DEV, create=not self._update)
        except KeyError:
            raise CommandError("Device item '%s' not found." % (devpath,))
        if not self._update:
            await dev.set('type', typepath, sync=False)
        if name:
            await dev.set('name', name, sync=False)
        if descr:
            await dev.set('descr', descr, sync=False)
        if data:
            d = await dev.subdir('data', create=None)
            for k,v in data.items():
                if k.startswith("input/") or k.startswith("output/"):
                    dx = dev
                else:
                    dx = d
                if v == "":
                    try:
                        await dx.delete(k, sync=False)
                    except KeyError:
                        pass
                else:
                    await dx.set(k.split('/'),v, sync=False)
            

class AddCommand(_AddUpdate,Command):
    name = "add"
    summary = "add an external device"
    description = """\
Create an entry for a new external device.

Arguments:

* the device's path (must not exist)

* the data type (must exist)

* data=value parameters (entry-specific, optional)

* a descriptive name (not optional)

Data items:

* input/topic (AMQP) for receiving state
* output/topic (AMQP) for sending state updates
* input/value and output/value: the JSON element which contains the data
* async (integer) if sending the output directly changes the value
  if not present, use RPC, wait for a reply.
  if zero, don't wait, assume yes..
  Otherwise wait this many seconds for the input alert.

"""
    _update = False
class UpdateCommand(_AddUpdate,Command):
    name = "change"
    summary = "change an external device"
    description = """\
Update an external device's entry.

Arguments:

* the device's path (required)

* data=value entries (deletes the key if value is empty)

  * in particular, input/topic=some.amqp.topic
    (and/or output/topic) is required

* a descriptive name (optional, to update)

The data type is immutable.

"""
    _update = True

class DeleteCommand(DefSetup,Command):
    name = "delete"
    summary = "Delete an external device"
    description = """\
External devices are stored in etcd at /dev/extern/**/:dev.

This command deletes one of these entries.
"""

    def addOptions(self):
        self.parser.add_option('-r','--recursive',
            action="store_true", dest="recursive",
            help="Delete all sub-devices")

    async def do(self,args):
        t = await self.setup()
        if not args:
            if not cmd.root.cfg['testing']:
                raise CommandError("You can't delete everything.")
            if not self.options.recursive:
                raise CommandError("You can't delete everything non-recursively.")
            await t.delete(recursive=True)
            return
        for k in args:
            try:
                dev = await t.subdir(k,name=DEV, create=False)
            except KeyError:
                raise CommandError("%s: does not exist"%k)
            if self.root.verbose:
                print("%s: deleted"%k, file=self.stdout)
            rec=self.options.recursive
            while True:
                p = dev._parent
                if p is None: break
                p = p()
                if p is None: break
                if p is t: break
                try:
                    await dev.delete(recursive=rec)
                except etcd.EtcdDirNotEmpty:
                    break
                rec=False
                dev = p

class DeviceCommand(SubCommand):
        name = "extern"
        summary = "Configure an external device"
        description = """\
Commands to configure external devices.
"""

        # process in order
        subCommandClasses = [
                ListCommand,
                AddCommand,
                UpdateCommand,
                DeleteCommand,
        ]


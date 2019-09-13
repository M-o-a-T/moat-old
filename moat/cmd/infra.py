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
from etcd_tree import EtcAwaiter
from collections.abc import Mapping

from moat.script import Command, SubCommand, CommandError
from moat.infra import INFRA_DIR, INFRA, LinkExistsError
from moat.util import r_dict, r_show
from moat.cmd.task import _ParamCommand

import logging
logger = logging.getLogger(__name__)

__all__ = ['InfraCommand']

class DefSetup:
    DIR = INFRA_DIR

    async def setup(self):
        await super().setup()
        etc = self.root.etcd
        tree = await self.root._get_tree()
        t = await tree.subdir(self.DIR)
        return t

class ListCommand(DefSetup,Command):
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
        t = await self.setup()
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
            rec = True
            while True:
                p = tt._parent
                if p is None: break
                p = p()
                if p is None: break
                if p is t: break
                try:
                    await tt.delete(recursive=rec)
                except etcd.EtcdDirNotEmpty:
                    if rec:
                        raise
                    break
                rec=False
                tt = p

async def copy(val, dest, name):
    if isinstance(val, Mapping):
        dest = await dest.subdir(name) # , create=True)
        for k,v in val.items():
            if isinstance(v, EtcAwaiter):
                v = await v
            await copy(v,dest,k)
    else:
        await dest.set(name,val)


class MoveCommand(DefSetup,Command):
    name = "move"
    summary = "Move an infrastructure entry"
    description = """\
Infrastructure entries are stored in etcd at /infra/**/:host.

This command moves one of these entries, by recreating the structure and
changing the entries they point to.
"""

    async def do(self,args):
        t = await self.setup()
        if len(args) != 2:
            raise CommandError("Move FROM TO. FROM must exist, TO must not.")
        p1 = tuple(args[0].split('.'))[::-1]
        p2 = tuple(args[1].split('.'))[::-1]
        try:
            t1 = await t.subdir(p1,name=INFRA, create=False)
        except KeyError:
            raise CommandError("%s does not exist" % (args[0],))
        try:
            t2 = await t.subdir(p2,name=INFRA, create=True)
        except etcd.EtcdAlreadyExist:
            raise CommandError("%s exists" % (args[1],))

        path = tuple(args[0].split('.'))[::-1]
        for k,v in t1.items():
            if k == "ports":
                v = await v
                for pn,pd in v.items():
                    if isinstance(pd, EtcAwaiter):
                        pd = await pd
                    try:
                        ph = pd['host']
                    except KeyError:
                        # probably a link
                        continue
                    try:
                        pp = pd['port']
                    except KeyError:
                        pass
                    else:
                        hh = tuple(ph.split('.'))[::-1]
                        hh = await t.subdir(hh,name=INFRA, create=False)
                        po = hh.lookup('ports',pp,'host')
                        if isinstance(po, EtcAwaiter):
                            po = await po
                        if po.value != args[0]:
                            logger.warn("Owch: back pointer for %s (%s on %s) is %s", pn,pp,ph,po.value)
                            continue
                        await hh.set('ports', value={pp:{'host':args[1]}})
            await copy(v,t2,k)

        rec = True
        while True:
            p = t1._parent
            if p is None: break
            p = p()
            if p is None: break
            if p is t: break
            try:
                await t1.delete(recursive=rec)
            except etcd.EtcdDirNotEmpty:
                if rec:
                    raise
                break
            rec = False
            t1 = p

class PortCommand(DefSetup,Command):
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
                print(a)
            else:
                if v == '':
                    await h.delete(k)
                else:
                    await h.set(k,v, ext=True)

class LinkCommand(DefSetup,Command):
    name = "link"
    summary = "Link two infrastructure items"
    description = """\
Link two devices.

Usage: … link HOST_A PORT_A HOST_B PORT_B -- join
       … link HOST_A PORT_A LINK_         -- link name
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
        self.parser.add_option('-r','--replace',
            action="store_true", dest="replace",
            help="overwrite existing links")

    async def do(self, args):
        t = await self.setup()
        if self.options.delete:
            if self.options.missing or self.options.replace:
                raise SyntaxError("'-d' and '-m'/'-r' cannot be used at the same time.")
            if len(args) != 2:
                raise SyntaxError("You need to specify which host+port to delete.") 
        else:
            if self.options.replace and len(args) < 3:
                raise SyntaxError("'-r' is only useful when creaing a link")
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
            is_link = False
            try:
                p2 = await t.host(args[2], create=False)
            except KeyError:
                is_link = True
                p2 = args[2]
                if self.root.verbose:
                    print("Creating a link.", file=sys.stderr)
            else:
                if len(args) == 4:
                    p2 = await p2.subdir('ports',args[3])
            try:
                await p1.link(p2, replace=self.options.replace)
            except LinkExistsError as e:
                port = e.args[0]
                try:
                    rem = await port.remote
                except KeyError:
                    print("Port %s:%s is linked to %s. Use '-r'." % (port.host.dnsname, port.name, port['host']), file=sys.stderr)
                else:
                    print("Port %s:%s is linked to %s:%s. Use '-r'." % (port.host.dnsname, port.name, rem.host.dnsname,rem.name), file=sys.stderr)

def VL(x):
    if x == '-':
        return set()
    elif x == '*':
        return set(('*',))
    return set(int(v) for v in x.split(','))

class NoVlanError(RuntimeError):
    pass

class CDict(dict):
    def add(self,k):
        self[k] = self.get(k,0)+1
    def keys(self):
        for k,v in self.items():
            if v > 1:
                yield k
    def __ior__(self, kk):
        for k in kk:
            self.add(k)
        return self

class VlanInfo:
    def __init__(self, host, t, verbose=1, seen=None):
        self.t = t
        self.verbose = verbose
        self.host = host
        self.ports = dict()  # name > vli
        self.vlans = CDict()

    def __repr__(self):
        return "<vli:%s>" % (self.host.dnsname,)

    async def extend(self, seen=None):
        sn = self.host.dnsname
        if seen is None:
            seen = set()
        elif sn in seen:
            return
        seen.add(sn)
        try:
            v = VL(self.host['vlan'])
        except KeyError:
            raise NoVlanError(self.host.dnsname)
        if not v:
            return
        self.vlans |= v
        try:
            pp = self.host['ports']
        except KeyError:
            return
        for n,p in pp.items():
            if 'vlan' in p:
                v = VL(p['vlan'])
                try:
                    h = p['host']
                except KeyError:
                    h = None
            else:
                try:
                    h = p['host']
                except KeyError:
                    continue
                hv = await self.t.host(h, create=False)
                hv = VlanInfo(hv, self.t, verbose=self.verbose)
                await hv.extend(seen)
                v = hv.vlans
            self.ports[n] = (v,h)
            self.vlans |= v

class VlanCommand(DefSetup,Command):
    name = "vlan"
    summary = "Show per-port VLAN configuration"
    description = """\
Show a router's required VLAN configuration.
That is, trace which VLANs are connected to each port, directly or indirectly.

Usage: … vlan HOST VLAN[,VLAN…]       -- set VLAN(s) which this host uses
       … vlan HOST PORT VLAN[,VLAN…]  -- set VLAN(s) on this port
       … vlan HOST                    -- list ports and connected VLAN(s)
       … vlan -v HOST                 -- list VLANs and connected ports

Setting VLANs on a port prevents that port from being followed when
collecting VLAN IDs.

Special VLANs (only on hosts) are
* -- pass-through
- -- special device, no VLAN
"""

    def addOptions(self):
        self.parser.add_option('-v','--vlans',
            action="store_true", dest="vlans",
            help="list per vlan, not per port")

    async def do(self, args):
        t = await self.setup()
        if len(args) < 1:
            raise SyntaxError("You need to specify host+port of both sides.") 
        elif len(args) == 1:
            h = await t.host(args[0],create=False)
            vli = VlanInfo(h,t)
            await vli.extend()
            if self.options.vlans:
                for vl in sorted(-1 if v == '*' else v for v in vli.vlans.keys()):
                    print('*' if vl==-1 else vl, ' '.join(sorted(str(p) for p,v in vli.ports.items() if ('*' if vl==-1 else vl) in v[0])))
            else:
                for p,vl in sorted(vli.ports.items()):
                    vl,n = vl
                    if vl:
                        vl = ','.join(str(x) for x in vl)
                    else:
                        vl = '-'
                    print(p, vl, n)
        elif len(args) == 2:
            h = await t.host(args[0],create=False)
            await h.set('vlan', args[1], sync=False)
        elif len(args) == 3:
            h = await t.host(args[0],create=False)
            p = h['ports'][args[1]]
            await p.set('vlan',args[2], sync=False)
        else:
            raise SyntaxError("Too many arguments.") 

class PathCommand(DefSetup,Command):
    name = "path"
    summary = "Show paths from A to B, or unreachables from A"
    description = """\
Show how A and B are linked, or which devices are not reachable from A.

Usage: … link HOST_A HOST_B -- show path
       … link HOST          -- list unreachable hosts

Links are unidirectional.
"""

    async def do(self, args):
        t = await self.setup()
        if len(args) < 0 or len(args) > 2:
            raise SyntaxError("Usage: … link HOST_A [HOST_B]")

        elif len(args) == 1: ## list unreachables
            hosts = [t.host(args[0])]
            known = set()
            while hosts:
                h = await hosts.pop()
                known.add(h.dnsname)
                try:
                    x = h['ports'].values()
                except KeyError:
                    pass
                else:
                    for v in x:
                        try:
                            v = v.get('host', raw=True)
                        except KeyError:
                            pass
                        else:
                            if v.value not in known:
                                hosts.append(v.host)
            async for h in t.tagged(INFRA):
                name = h.dnsname
                if name not in known:
                    print(name)

        else: ## list links
            dest = await t.host(args[1])
            dname = dest.dnsname
            hosts = [t.host(args[0])]
            prevs = {args[0]: None}
            while hosts:
                h = await hosts.pop(0)
                try:
                    hp = h['ports']
                except KeyError:
                    continue
                for v in hp.values():
                    try:
                        v = v.get('host', raw=True)
                    except KeyError:
                        continue
                    if v.value == dname:
                        def prev_p(name):
                            if name is None:
                                return
                            prev_p(prevs[name])
                            print(name)
                        prev_p(h.dnsname)
                        print(v.value)
                        return
                    if v.value not in prevs:
                        prevs[v.value] = h.dnsname
                        hosts.append(v.host)
            print("Unreachable.", file=sys.stderr)

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
                VlanCommand,
                PathCommand,
                UpdateCommand,
                MoveCommand,
                DeleteCommand,
        ]


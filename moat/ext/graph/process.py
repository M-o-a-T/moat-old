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

from sqlmix.async import NoData
from datetime import datetime,timedelta
import attr
import sys
from functools import partial

import logging
logger = logging.getLogger(__name__)

### types for "raw" data

class DoNothing(Exception):
    pass

@attr.s
class _data(object):
    """\
        One data record (abstract)
        """
    id = attr.ib(default=None)
    data_type = attr.ib(default=None)
    value = attr.ib(default=0)
    aux_value = attr.ib(default=0)
    timestamp = attr.ib(default=None)

    def set(self, **kv):
        """load attributes (from database record (needs to be a hash))"""
        super().__init__() # set to default values
        for k,v in kv.items():
            setattr(self,k,v)

    def reset(self, ts):
        self.timestamp = ts
        self.id = None
        self.value = 0
        self.aux_value = 0

    def __init__(self, proc):
        self.proc = proc
        self.db = proc.db

@attr.s
class data(_data):
    """\
        One non-aggregated data record :: data_log
        """
    @property
    def min_value(self):
        return self.value
    @property
    def max_value(self):
        return self.value
    @property
    def tsc(self):
        return self.timestamp.timestamp()
    @property
    def n_values(self):
        return 1
    def in_tsc(self,other):
        return other.timestamp == self.timestamp
    def tsc_of(self,ts):
        return ts.timestamp()
    def ts_of(self,ts):
        return ts

@attr.s
class _agg(_data):
    """\
        One aggregated data record :: data_agg
        """
    min_value = attr.ib(default = sys.float_info.max)
    max_value = attr.ib(default = -sys.float_info.max)
    tsc = attr.ib(default=None)
    n_values = attr.ib(default = 0)

class agg(_agg):
    updated = False

    def __init__(self, atype):
        """@atype: agg_type record"""
        super().__init__()
        _data.__init__(self,atype.proc)
        self.atype = atype
        self.db = self.atype.db
    
    def in_tsc(self,other):
        """check whether the timestamp of 'other' is in this """
        return self.tsc == self.tsc_of(other.timestamp)

    def tsc_of(self, ts, interval=None):
        """some timestamp => timestamp counter for the interval it's in"""
        if interval is None:
            interval = self.atype.interval
        return ts.timestamp() // interval

    def ts_of(self, ts, offset=0):
        """some timestamp => start time of the interval it's in"""
        return datetime.utcfromtimestamp((self.tsc_of(ts)+offset) * self.atype.interval)

    @property
    def start_ts(self):
        return self.ts_of(self.timestamp)

    @property
    def end_ts(self):
        return self.ts_of(self.timestamp,1)

    def reset(self, ts):
        """Reset for a specific timestamp"""
        super().reset(ts)
        self.tsc = self.tsc_of(self.timestamp)
        self.min_value = sys.float_info.max
        self.max_value = -sys.float_info.max
        self.n_values = 0
        self.updated = False
    
    async def load(self, **kv):
        """read a specific record"""
        self.tsc = None
        d = await self.db.DoFn("select * from data_agg where "+' and '.join("%s=${%s}"%(k,k) for k in kv.keys()), **kv, _dict=True)
        self.set(**d)
        self.updated = False
        if not self.tsc:
            self.tsc = self.tsc_of(self.timestamp)
            self.updated = True

    async def save(self):
        """write the current record"""
        if not self.updated:
            return
        if self.id is not None:
            logger.debug("N %s", self)
            await self.db.Do("update data_agg set value=${value},aux_value=${aux_value},min_value=${min_value},max_value=${max_value},n_values=${n_values},timestamp=${timestamp} where id=${id}", _empty=True, **attr.asdict(self))
            # tsc must no change
        elif self.n_values > 0:
            logger.debug("U %s", self)
            self.id = await self.db.Do("insert into data_agg(data_agg_type,value,aux_value,min_value,max_value,n_values,timestamp,tsc) values(${lid},${value},${aux_value},${min_value},${max_value},${n_values},${timestamp},${tsc})", lid=self.atype.id, **attr.asdict(self))

    async def read(self, ts):
        if self.timestamp == ts:
            return
        await self.load(data_agg_type=self.proc.dtid, timestamp=ts)

### Handle data processing

class _proc:
    """Base class for processing a single record"""
    agg = None

    def __init__(self, typ):
        """\
            @typ: agg_type record
            """
        self.typ = typ
        self.db = self.typ.db

    async def startup(self, data):
        """\
            Hook to open the current record

            E.g. collect usage for the range [start_ts,data_ts[
            """
        self.agg = agg(self.typ)
        try:
            await self.agg.load(data_agg_type=self.typ.id, timestamp=self.agg.ts_of(data.timestamp))
        except NoData:
            self.agg.reset(data.timestamp)

    async def finish(self, data=None):
        """
            Hook to close the current record

            E.g. collect usage for the range [old_data_ts,end_ts[

            WARNING: this will be called with the *new* record
            (or None, if at the end of the current run).
            """
        if self.agg is None:
            return
        if self.agg.n_values:
            await self.agg.save()

    async def run(self, data):
        """\
            add this to our aggregation
            """
        logger.debug("R %s",data)
        if self.agg and not self.agg.in_tsc(data):
            await self.finish(data)
        if not self.agg or not self.agg.in_tsc(data):
            await self.startup(data)
        if not self.process(data):
            self.update_ts(data)

    def process(self, data):
        """Process this data record.
            Return True to skip updating the aggregate's timestamp."""
        raise NotImplementedError

    def update_ts(self,data):
        """Update the aggregate's timestamp."""
        self.typ.timestamp = data.timestamp
        self.typ.updated = True

    async def cleanup(self):
        pass # don't

class _proc_clean(object):
    """Mix-in to clean up entries before our min date"""
    async def cleanup(self):
        if not self.typ.max_age:
            return
        ts = self.typ.timestamp - timedelta(0,self.typ.max_age) # how long to keep
        try:
            lts, = await self.db.DoFn("select timestamp from data_agg_type where data_type=${id} and layer=${layer}", id=self.typ.data_type, layer=self.typ.layer+1)
        except NoData:
            pass
        else:
            if ts > lts: # don't kill unprocessed data
                ts = lts

        if self.typ.layer == 0:
            n = await self.db.Do("delete from data_log where data_type=${typ} and timestamp < ${ts}", typ=self.typ.data_type, ts=ts, _empty=True)
        else:
            agg, = await self.db.DoFn("select id from data_agg_type where data_type=${typ} and layer=${layer}", typ=self.typ.data_type, layer=self.typ.layer-1, )
            n = await self.db.Do("delete from data_agg where data_agg_type=${agg} and timestamp < ${ts}", ts=ts, agg=agg, _empty=True)
        if n:
            logger.debug("%s records deleted for %s/%s", n, self.typ.tag,self.typ.layer)

class proc_noop(_proc):
    """do not do anything"""
    def process(self,data):
        raise DoNothing

class proc_ignore(_proc):
    """do not do anything"""
    def process(self,data):
        pass

class proc_delete(_proc_clean, proc_ignore):
    """do not do anything; just delete the data"""
    pass

class proc_store(proc_delete):
    """Save an average continuous value (power use, temperature, humidity) with min/max ranges"""
    def process(self,data):
        on = self.agg.n_values
        self.agg.n_values += data.n_values
        self.agg.value = (self.agg.value * on + data.value * data.n_values) / self.agg.n_values
        self.agg.aux_value = (self.agg.aux_value * on + data.aux_value * data.n_values) / self.agg.n_values
        self.agg.min_value = min(data.min_value,self.agg.min_value)
        self.agg.max_value = max(data.max_value,self.agg.max_value)
        self.agg.updated = True

class proc_count(proc_store):
    """Save an increasing discrete value (rain gauge, lightning counter).
        The first increase within an interval gets credited to that interval"""
    DISC=True
    def process(self,data):
        dv = data.value
        dav = data.aux_value
        if self.typ.layer == 0: # need to aggregate
            if dv >= self.typ.value and dav >= self.typ.aux_value:
                dv = dv - self.typ.value
                dav = dav - self.typ.aux_value
            self.typ.value = data.value
            self.typ.aux_value = data.aux_value
            self.typ.updated = True
            # need to distribute data across interval
            ln = data.timestamp() - self.typ.timestamp.timestamp()
            self.agg.min_value = min(self.agg.min_value,dv/ln)
            self.agg.max_value = max(self.agg.max_value,dv/ln)
        else:
            self.agg.min_value = min(self.agg.min_value,data.min_value)
            self.agg.max_value = max(self.agg.max_value,data.max_value)
        self.agg.value += dv
        self.agg.aux_value += dav
        self.agg.updated = True
        
class proc_cont(proc_count):
    """Save an increasing continuous value (power meter)
        The first increase within an interval is distributed between the
        previous and the new range
        """
    DISC=False
    async def startup(self,data):
        if self.typ.layer > 0:
            await super().startup(data)
            return
        import pdb;pdb.set_trace()
        self.typ.timestamp
        self.agg = None

        dv = data.value
        dav = data.aux_value
        
class proc_event(proc_store):
    """Single event (button pressed):
        multiple events within L0 are counted normally"""
    def process(self,data):
        self.agg.n_values += data.n_values
        self.agg.value += data.value
        self.agg.aux_value = data.aux_value
        self.agg.min_value = min(self.agg.value,self.agg.min_value)
        self.agg.max_value = max(self.agg.value,self.agg.max_value)
        self.agg.updated = True

class proc_notice(proc_event):
    """Single event (motion detected):
        multiple events within L0 are counted once,
        requires guard interval to resume counting"""

    async def startup(self,data):
        if self.typ.layer > 0 and self.agg is not None:
            t_next = self.agg.tsc_of(self.agg.timestamp + timedelta(0,self.typ.prev_interval))
            t_data = self.agg.tsc_of(data.timestamp)
            if self.agg.tsc == t_next and t_data > t_next:
                self.agg.min_value = 0
                self.agg.updated = True
                await self.agg.save()
            
        await super().startup(data)
        if self.typ.layer == 0:
            return
        t_this = self.agg.tsc_of(self.agg.start_ts, self.typ.prev_interval)
        t_data = self.agg.tsc_of(data.timestamp, self.typ.prev_interval)
        if t_this != t_data:
            self.agg.min_value = 0
            self.agg.updated = True

    def process(self,data):
        if data.value == 0:
            return True # skip update_ts
        if self.typ.layer > 0:
            self.agg.n_values += 1
            self.agg.value += data.value
            self.agg.aux_value = data.aux_value
            self.agg.min_value = min(self.agg.value,self.agg.min_value)
            self.agg.max_value = self.agg.value+self.agg.max_value
            self.agg.updated = True
            return
        t_last = self.agg.tsc_of(self.typ.timestamp)
        t_data = self.agg.tsc_of(data.timestamp)
        if t_last+1 < t_data:
            self.agg.n_values = 1
            self.agg.value = 1
            self.agg.aux_value = 0
            self.agg.min_value = 1
            self.agg.max_value += 1
            self.agg.updated = True
        return

class proc_cycle(proc_store):
    """Cyclic values with confidence (wind direction)
        """
    def process(self,data):
        raise NotImplementedError

from . import modes
procs = {}
for k,v in modes.items():
    try:
        procs[k] = globals()['proc_'+v[0]]
    except KeyError:
        logger.warning("No processing module for mode=%s",v[0])
        procs[k] = proc_noop

### control record for processing

@attr.s
class _agg_type(object):
    """\
        Aggregated record type :: data_agg_type
        """
    id = attr.ib(default=None)
    data_type = attr.ib(default=None)
    layer = attr.ib(default=None)
    max_age = attr.ib(default=None)
    interval = attr.ib(default=None)
    timestamp = attr.ib(default=None)
    ts_last = attr.ib(default=None)
    value = attr.ib(default=0)
    aux_value = attr.ib(default=0)

class agg_type(_agg_type):
    updated = False
    proc = None

    SAVE_SQL = ', '.join("`%s`=${%s}" % (k,k) for k in 'value aux_value timestamp ts_last'.split())

    def __init__(self, proc, db):
        super().__init__()
        self.proc = proc
        self.db = db

    async def load(self, id):
        self.id = id
        d = await self.db.DoFn("select * from data_agg_type where id=${id}", id=self.id)
        await self.set(d)
    
    async def save(self, force=False):
        if force or self.updated:
            await self.proc.finish()
            await self.db.Do("update data_agg_type set "+self.SAVE_SQL+" where id=${id}", _empty=True, **attr.asdict(self))
            self.updated = False
    
    async def set(self, d):
        super().__init__() # set to default values
        for k,v in d.items():
            setattr(self,k,v)
        if self.layer > 0:
            self.prev_interval, = await self.db.DoFn("select `interval` from data_agg_type where data_type=${dtid} and layer=${layer}", dtid=self.data_type, layer=self.layer-1)
        else:
            self.prev_interval = 0
        self.updated = False
        self.mode,self.tag = await self.db.DoFn("select `method`,`tag` from data_type where id=${id}", id=self.data_type)
        self.proc = procs[self.mode](self)

    async def process(self, d):
        await self.proc.run(d)

    async def run(self):
        if self.layer == 0:
            dtyp = data
        else:
            dtyp = partial(agg,self)
        try:
            tm=self.ts_last or self.timestamp
            while True:
                if self.layer == 0: # process raw data
                    r = self.db.DoSelect("select * from data_log where data_type=${dtid} and timestamp > ${tm} order by timestamp limit 100", dtid=self.data_type, tm=tm, _dict=True)

                else: # process previous layer
                    llid, = await self.db.DoFn("select id from data_agg_type where data_type=${dtid} and layer=${layer}", layer=self.layer-1, dtid=self.data_type, tm=tm)
                    r = self.db.DoSelect("select * from data_agg where data_agg_type=${llid} and timestamp > ${tm} order by timestamp limit 100", llid=llid, tm=tm, _dict=True)
                dt = dtyp()

                async for d in r:
                    dt.set(**d)
                    await self.process(dt)
                    tm=dt.timestamp

        except DoNothing:
            pass # oh well
        except NoData:
            self.ts_last = tm
            await self.proc.finish()
            await self.proc.cleanup()
            await self.save(True)


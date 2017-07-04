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
from qbroker.util import UTC

import logging
logger = logging.getLogger(__name__)

### types for "raw" data

class DoNothing(Exception):
    pass

class BackTime(Exception):
    def __init__(self,id,timestamp):
        self.id = id
        self.timestamp = timestamp
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
        if 'timestamp' in kv and self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

    def reset(self, ts):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
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
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.timestamp() // interval

    def ts_of(self, ts, offset=0):
        """some timestamp => start time of the interval it's in"""
        return datetime.utcfromtimestamp((self.tsc_of(ts)+offset) * self.atype.interval).replace(tzinfo=UTC)

    @property
    def start_ts(self):
        return self.ts_of(self.timestamp)

    @property
    def end_ts(self):
        return self.ts_of(self.timestamp,1)

    def reset(self, ts, at_start=False):
        """Reset for a specific timestamp"""
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        super().reset(ts)
        self.tsc = self.tsc_of(self.timestamp)
        if at_start:
            self.timestamp = self.start_ts
        self.min_value = sys.float_info.max
        self.max_value = -sys.float_info.max
        self.n_values = 0
        self.updated = False
    
    async def load(self, **kv):
        """read a specific record"""
        self.tsc = None
        sel = ' and '.join("%s=${%s}"%(k,k) for k in kv.keys())
        if sel:
            sel = ' and '+sel
        d = await self.db.DoFn("select * from data_agg where data_agg_type=${dtid}"+sel+" order by tsc desc limit 1", dtid=self.atype.id, **kv, _dict=True)
        self.set(**d)
        self.updated = False
        if not self.tsc:
            self.tsc = self.tsc_of(self.timestamp)
            self.updated = True

    async def save(self):
        """write the current record"""
        if not self.updated:
            return
        self.min_value = min(self.value,self.min_value)
        self.max_value = max(self.value,self.max_value)
        if self.id is not None:
            logger.debug("U %s", self)
            await self.db.Do("update data_agg set value=${value},aux_value=${aux_value},min_value=${min_value},max_value=${max_value},n_values=${n_values},timestamp=${timestamp} where id=${id}", _empty=True, **attr.asdict(self))
            # tsc must no change
        elif self.n_values > 0 or self.value != 0:
            logger.debug("N %s", self)
            self.id = await self.db.Do("insert into data_agg(data_agg_type,value,aux_value,min_value,max_value,n_values,timestamp,tsc) values(${lid},${value},${aux_value},${min_value},${max_value},${n_values},${timestamp},${tsc})", lid=self.atype.id, **attr.asdict(self))

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

    def do_rollback(self, dt1, dt2):
        """The part of .rollback() that does the actual work"""
        pass

    async def rollback(self, dt1, dt2):
        """\
            When deleting data, dt is the first record of the following timespan.
            Thus when doing some sort of continuous recording we need to
            subtract that delta.

            @dt1 is the newest record within the current set.
            @dt2 is the oldest new record that's going to be deleted.
            """
        if self.agg is None:
            self.agg = agg(self.typ)
        await self.agg.load(tsc=self.agg.tsc_of(dt1.timestamp))
        self.do_rollback(dt1,dt2)
        
        self.timestamp = dt1.timestamp
        self.last_id = dt1.id
        self.agg.timestamp = dt1.timestamp
        self.agg.updated = True
        await self.agg.save()

    async def startup(self, data):
        """\
            Hook to open the current record

            E.g. collect usage for the range [start_ts,data_ts[
            """
        if self.agg is None:
            self.agg = agg(self.typ)
        try:
            await self.agg.load(tsc=self.agg.tsc_of(data.timestamp))
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
        if not (await self.process(data)):
            self.update_ts(data)

    async def process(self, data):
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
        ts = self.typ.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        ts = ts-timedelta(0,self.typ.max_age) # how long to keep

        if self.typ.layer == 0:
            n = await self.db.Do("delete from data_log where data_type=${typ} and timestamp < ${ts} and id < ${last_id}", typ=self.typ.data_type, ts=ts, last_id=self.typ.last_id, _empty=True)
            await self.db.Do("update data_type set n_values=n_values-${n} where id=${typ}", n=n, typ=self.typ.data_type, _empty=True)
            await self.db.Do("update data_type set n_values=0 where id=${typ} and n_values<0", typ=self.typ.data_type, _empty=True)
        else:
            agg, = await self.db.DoFn("select id from data_agg_type where data_type=${typ} and layer=${layer}", typ=self.typ.data_type, layer=self.typ.layer-1, )
            n = await self.db.Do("delete from data_agg where data_agg_type=${agg} and timestamp < ${ts} and id < ${last_id}", ts=ts, agg=agg, last_id=self.typ.last_id, _empty=True)
        if n:
            logger.debug("%s records deleted for %s/%s", n, self.typ.tag,self.typ.layer)

class proc_noop(_proc):
    """do not do anything"""
    async def process(self,data):
        raise DoNothing

class proc_ignore(_proc):
    """do not do anything"""
    async def process(self,data):
        pass

class proc_delete(_proc_clean, proc_ignore):
    """do not do anything; just delete the data"""
    pass

class proc_store(proc_delete):
    """Save an average continuous value (power use, temperature, humidity) with min/max ranges"""
    async def process(self,data):
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
    async def process(self,data):
        dv = data.value
        dav = data.aux_value
        if self.typ.layer == 0: # need to aggregate
            if self.typ.value is None or dv < self.typ.value:
                self.typ.value = dv
            else:
                dv -= self.typ.value
                self.typ.value += dv
            if self.typ.aux_value is None or dav < self.typ.aux_value:
                self.typ.aux_value = dav
            else:
                dav -= self.typ.aux_value
                self.typ.aux_value += dav
            self.typ.updated = True
            # need to distribute data across interval
            ln = data.timestamp.timestamp() - self.typ.timestamp.timestamp()
            if ln > 0:
                self.agg.min_value = min(self.agg.min_value,dv/ln)
                self.agg.max_value = max(self.agg.max_value,dv/ln)
        else:
            self.agg.min_value = min(self.agg.min_value,data.min_value)
            self.agg.max_value = max(self.agg.max_value,data.max_value)
        self.agg.value += dv
        self.agg.aux_value += dav
        self.agg.updated = True
        
class _proc_start:
    """Mix-in to load the latest, i.e. not necessarily the current, record"""
        
    async def startup(self, data):
        """\
            Hook to open the current record

            E.g. collect usage for the range [start_ts,data_ts[
            """
        if self.typ.layer > 0:
            await super().startup(data)
            return

        if self.agg is None:
            self.agg = agg(self.typ)
        try:
            await self.agg.load()
        except NoData:
            self.agg.reset(data.timestamp, at_start=True)

        else:
            if self.agg.timestamp > data.timestamp:
                raise BackTime(data.id,data.timestamp)

class proc_cont(_proc_start, proc_count):
    """Save an increasing continuous value (power meter)
        The first increase within an interval is distributed between the
        previous and the new range
        """
    DISC=False

    async def process(self,data):
        if self.typ.layer > 0:
            await super().process(data)
            return
        tsc = self.agg.tsc_of(data.timestamp)
        dv = data.value
        dav = data.aux_value

        # first record / counter cleared?
        if self.typ.value is None or self.typ.value > data.value:
            self.typ.value = data.value
            self.typ.timestamp = data.timestamp
        if self.typ.aux_value is None or self.typ.aux_value > data.aux_value:
            self.typ.aux_value = data.aux_value

        dv -= self.typ.value
        dav -= self.typ.aux_value
        td = (data.timestamp - self.typ.timestamp).total_seconds()

        if td > 0 and dv > 0:
            while self.agg.tsc < tsc:
                self.agg.value += dv * (self.agg.end_ts-self.agg.timestamp).total_seconds()/td
                self.agg.aux_value += dav * (self.agg.end_ts-self.agg.timestamp).total_seconds()/td
                self.agg.updated = True
                await self.agg.save()
                self.agg.reset(self.agg.end_ts)
        if self.agg.tsc != tsc: # while loop not entered
            self.agg.reset(data.timestamp)
        else:
            self.agg.timestamp = data.timestamp
        if td > 0:
            self.agg.value += dv * (data.timestamp-self.agg.timestamp).total_seconds()/td
            self.agg.aux_value += dav * (data.timestamp-self.agg.timestamp).total_seconds()/td
            self.agg.n_values += 1

        self.agg.updated = True

        self.typ.value = data.value
        self.typ.aux_value = data.aux_value
        self.typ.updated = True

    def do_rollback(self, dr1,dr2):
        f = (self.agg.end_ts-max(self.agg.start_ts,dr1.timestamp))/(dr2.timestamp-dr1.timestamp)
        assert 0 <= f <= 1, (f,self.agg,dr1,dr2)
        self.agg.value -= (dr2.value-dr1.value)*f
        self.agg.aux_value -= (dr2.aux_value-dr1.aux_value)*f

class proc_persist(proc_cont):
    """persistent changes (light switch),
        records the percentage of time the thing was on"""
    async def process(self,data):
        if self.typ.layer > 0:
            await super().process(data)
            return
        tsc = self.agg.tsc_of(data.timestamp)
        if self.typ.value or self.typ.aux_value:
            while self.agg.tsc < tsc:
                self.agg.value += self.typ.value * (self.agg.end_ts-self.typ.timestamp).total_seconds()/self.typ.interval
                self.agg.aux_value += self.typ.aux_value * (self.agg.end_ts-self.typ.timestamp).total_seconds()/self.typ.interval
                self.agg.updated = True
                await self.agg.save()
                self.agg.reset(self.agg.end_ts)
                self.typ.timestamp = self.agg.timestamp

            assert self.agg.tsc == tsc, (self.agg.tsc,tsc)
            self.agg.value += self.typ.value * (data.timestamp-self.agg.timestamp).total_seconds()/self.typ.interval
            self.agg.aux_value += self.typ.aux_value * (data.timestamp-self.agg.timestamp).total_seconds()/self.typ.interval

        else:
            await super(_proc_start,self).startup(data) # get current record
        self.agg.min_value = min(self.agg.min_value,data.min_value)
        self.agg.max_value = max(self.agg.max_value,data.max_value)
        self.agg.n_values += 1
        self.agg.timestamp = data.timestamp
        self.agg.updated = True

class proc_event(proc_store):
    """Single event (button pressed):
        multiple events within L0 are counted normally"""
    async def process(self,data):
        self.agg.n_values += data.n_values
        self.agg.value += data.value
        self.agg.aux_value += data.aux_value
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

    async def process(self,data):
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
    async def process(self,data):
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
    last_id = attr.ib(default=0)
    value = attr.ib(default=0)
    aux_value = attr.ib(default=0)

class agg_type(_agg_type):
    updated = False
    proc = None

    SAVE_SQL = ', '.join("`%s`=${%s}" % (k,k) for k in 'value aux_value timestamp last_id'.split())

    def __init__(self, proc, db):
        super().__init__()
        self.proc = proc
        self.db = db

    async def load(self, id):
        self.id = id
        d = await self.db.DoFn("select * from data_agg_type where id=${id}", id=self.id)
        await self.set(d)
    
    async def save(self, force=False):
        if self.id is None:
            self.id = await self.db.Do("insert into data_agg_type(`data_type`,`layer`,`interval`,`max_age`,`timestamp`,`last_id`) values(${data_type},${layer},${interval},${max_age},${timestamp},${last_id})", **attr.asdict(self))
        if force or self.updated:
            await self.proc.finish()
            await self.db.Do("update data_agg_type set "+self.SAVE_SQL+" where id=${id}", _empty=True, **attr.asdict(self))
            self.updated = False
    
    async def set(self, d):
        super().__init__() # set to default values
        for k,v in d.items():
            setattr(self,k,v)
        if 'timestamp' in d and self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)
        if self.layer > 0:
            self.prev_interval, = await self.db.DoFn("select `interval` from data_agg_type where data_type=${dtid} and layer=${layer}", dtid=self.data_type, layer=self.layer-1)
        else:
            self.prev_interval = 0
        self.updated = False
        self.mode,self.tag = await self.db.DoFn("select `method`,`tag` from data_type where id=${id}", id=self.data_type)
        self.proc = procs[self.mode](self)

    async def process(self, d):
        await self.proc.run(d)
        self.value = d.value
        self.aux_value = d.aux_value
        self.last_id = d.id
        self.timestamp = d.timestamp
        self.updated = True

    async def rollback_h(self, ts):
        dt = agg(self)
        dt.reset(ts)
        await self.db.Do("delete from data_agg where data_agg_type=${aid} and timestamp>=${ts}", aid=self.id,ts=dt.start_ts, _empty=True)

        st = agg_type(self.proc,self.db)
        try:
            d = await self.db.DoFn("select * from data_agg_type where data_type=${dtid} and layer=${layer}", dtid=self.data_type, layer=self.layer+1, _dict=True)
        except NoData:
            pass
        else:
            await st.set(d)
            await st.rollback_h(ts)

    async def rollback(self, id,ts):
        assert self.layer == 0, self
        # first get the lowest new record
        nid,nts = await self.db.DoFn("select id,timestamp from data_log where data_type=${dtid} and id>${id} order by timestamp limit 1", dtid=self.data_type, id=self.last_id)
        if nts.tzinfo is None:
            nts = nts.replace(tzinfo=UTC)
        assert nts > self.timestamp-timedelta(0,self.max_age) # don't go beyond deleted data

        # first record to be deleted
        dt = agg(self)
        dt.reset(nts)
        d = await self.db.DoFn("select * from data_log where data_type=${dtid} and id<=${id} and timestamp>=${ts} order by timestamp limit 1", dtid=self.data_type, ts=dt.start_ts, id=self.last_id, _dict=True)
        dr2 = data()
        dr2.set(**d)
        assert dr2.timestamp > self.timestamp-timedelta(0,self.max_age) # don't go beyond deleted data

        # last record to be kept
        d = await self.db.DoFn("select * from data_log where data_type=${dtid} and timestamp<${ts} order by timestamp desc limit 1", dtid=self.data_type, ts=dt.start_ts, id=self.last_id, _dict=True)
        dr1 = data()
        dr1.set(**d)

        #await dt.load(tsc=dt.tsc-1)
        await self.proc.rollback(dr1,dr2)
        #dt.save()
        await dt.load(tsc=dt.tsc)
        await self.rollback_h(dt.start_ts)

        # update values
        self.value = dr1.value
        self.aux_value = dr2.value
        self.update = True

    async def run(self, cleanup=True):
        if self.layer == 0:
            dtyp = data
        else:
            dtyp = partial(agg,self)
            llid, = await self.db.DoFn("select id from data_agg_type where data_type=${dtid} and layer=${layer}", layer=self.layer-1, dtid=self.data_type)
            try:
                top, = await self.db.DoFn("select max(id) from data_agg where data_agg_type=${dtid}", dtid=llid)
            except NoData:
                top = None
                tops = ""
            else:
                tops = " and id < ${top}"
        try:
            if self.layer == 0: # process raw data
                r = self.db.DoSelect("select * from data_log where data_type=${dtid} and id > ${last_id} and timestamp > ${ts} order by timestamp,id", dtid=self.data_type, last_id=self.last_id, ts=self.timestamp-timedelta(1), _dict=True)

            else: # process previous layer
                r = self.db.DoSelect("select * from data_agg where data_agg_type=${llid} and id > ${last_id} and timestamp > ${ts}"+tops+" order by timestamp,id", llid=llid, last_id=self.last_id,top=top, ts=self.timestamp-timedelta(1), _dict=True)
            dt = dtyp()

            async for d in r:
                dt.set(**d)
                await self.process(dt)

        except BackTime as bt:
            logger.warning("Need Time fix %s:%d at %d:%s",self.tag,self.layer, bt.id,bt.timestamp)
            await self.rollback(bt.id,bt.timestamp)
            return
        except DoNothing:
            logger.info("Skipped %s:%d",self.tag,self.layer)
            return
        except NoData:
            return

        await self.proc.finish()
        if cleanup:
            await self.proc.cleanup()
        await self.save(True)


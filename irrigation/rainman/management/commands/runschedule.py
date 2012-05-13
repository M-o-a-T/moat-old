# -*- coding: utf-8 -*-

##
##  Copyright © 2012, Matthias Urlichs <matthias@urlichs.de>
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

"""\
		Run the current schedule, watch out for rain
		"""

from __future__ import division,absolute_import
from homevent import gevent_rpyc
gevent_rpyc.patch_all()

from traceback import format_exc,print_exc
import sys
import gevent,rpyc
from gevent.queue import Queue
from gevent.coros import Semaphore
from gevent.event import AsyncResult
from rpyc.core.service import VoidService
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller,History
from rainman.utils import now
from rainman.logging import log,log_error
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.db import transaction

class Command(BaseCommand):
	args = ''
	help = 'Run the current schedule, watch for rain, etc.'

	option_list = BaseCommand.option_list + (
		make_option('-s','--site',
			action='store',
			dest='site',
			default=None,
			help='Limit to this Site (all controllers)'),
		make_option('-c','--controller',
			action='store',
			dest='controller',
			default=None,
			help='Controller to generate a config file snippet for'),
		make_option('-t','--timeout',
			action='store',type='int',
			dest='timeout',
			default=600,
			help='Run main processing loop every N seconds'),
		)

	def handle(self, *args, **options):
		q = Q()
		if options['site']:
			q &= Q(site__name=options['site'])
		if options['controller']:
			q &= Q(name=options['controller'])
		for c in Controller.objects.filter(q):
			site = SchedSite(c.site)
			site.run_every(timedelta(0,options['timeout']))
			site.run_sched_task(True)
			controller = SchedController(c)
			controller.connect_monitors()

		if not controllers:
			raise RuntimeError("No matching controllers found.")
		while True:
			gevent.sleep(99999)



class RestartService(VoidService):
	def on_disconnect(self,*a,**k):
		for s in sites.itervalues():
			if s.ci._local_root is self:
				s.log("disconnected")
				s.ci = None
				s.run_main_task()
				gevent.spawn_later(10,s.maybe_restart)


class Meter(object):
	sum_it = False
	def __init__(self,dev):
		self.d = dev
		self.site = SchedSite(dev.site)

	@property
	def weight(self):
		return self.d.weight

	def monitor_value(self,event=None,**k):
		"""monitor value NUMBER name…"""
		try:
			print >>sys.stderr,self.__class__.__name__,self.d.name,event
			val = float(event[2])
			self.add_value(val)
		except Exception:
			print_exc()

	def refresh(self):
		self.d.refresh()

	def connect_monitors(self):
		if not self.d.var:
			return
		if self.site.ci is None:
			return
		print >>sys.stderr," ".join(("Connect to","monitor","value","*")+tuple(self.d.var.split()))
		self.mon = self.site.ci.root.monitor(self.monitor_value,"monitor","value","*",*(self.d.var.split()))

	def log(self,txt):
		self.site.log(("%s %s: "%(self.meter_type,self.d.name))+txt)

class SumMeter(Meter):
	sumval = 0
	def get_value(self):
		r,self.sumval = self.sumval,0
		return r
		
	def add_value(self,val):
		self.sumval += val

class RainMeter(SumMeter):
	meter_type="rain"

	def add_value(self,val):
		super(RainMeter,self).add_value(val)
		if val > 0:
			self.site.has_rain()

class FeedMeter(SumMeter):
	meter_type="feed"
	sum_it = True
	weight = 1
	def __init__(self,*a,**k):
		super(FeedMeter,self).__init__(*a,**k)
		self.valves = set()
		for v in self.d.valves.all():
			valve = SchedValve(v)
			valve.feed = self
			self.valves.add(valve)

	def add_value(self,val):
		super(FeedMeter,self).add_value(val)
		sum_f = 0
		for valve in self.valves:
			if valve.on:
				sum_f += valve.v.flow
		if sum_f:
			for valve in self.valves:
				if valve.on:
					valve.add_flow(val * valve.v.flow / sum_f)

	def check_flow(self,**k):
		for valve in self.valves:
			valve.check_flow(**k)

	def connect_monitors(self):
		super(FeedMeter,self).connect_monitors()
		self.chk = self.site.ci.root.monitor(self.check_flow,"check","flow",*(self.d.var.split()))

	
		
class AvgMeter(Meter):
	val = None
	avg = 0
	nval = 0
	ts = None

	def connect_monitors(self):
		super(AvgMeter,self).connect_monitors()
		self.ts = None

	def get_value(self):
		if self.ts is None:
			return None
		self.snapshot()
		if not self.nval:
			return None
		r = self.avg / self.nval
		self.avg = 0
		self.nval = 0
		return r

	def snapshot(self):
		n = now()
		if self.ts is not None and self.val is not None:
			w=(n-self.ts).total_seconds()
			if w > 300: w = 300 # if the measurer dies
			self.avg += w*self.val
			self.nval += w
		self.ts = n
	
	def add_value(self,val):
		self.snapshot()
		self.val = val

class TempMeter(AvgMeter):
	meter_type="temp"

class WindMeter(AvgMeter):
	meter_type="wind"

class SunMeter(AvgMeter):
	meter_type="sun"

METERS=[]
for m in globals().values():
	if hasattr(m,"meter_type"):
		METERS.append(m)


class SchedCommon(object):
	def log(self,txt):
		raise NotImplementedError("You forgot to implement %s.log" % (self.__class__.__name__,))
	def log_error(self,context=None):
		self.log(format_exc()+repr(context))

sites = {}
controllers = {}
paramgroups = {}
valves = {}

class ParamGroup(SchedCommon):
	"""Mirrors a parameter group for valves"""
	def __new__(cls,pargroup):
		if pargroup.id in paramgroups:
			return paramgroups[pargroup.id]
		self = object.__new__(cls)
		paramgroups[pargroup.id] = self
		self.pg = pargroup
		return self
	def __init__(self,site):
		pass

	def log(self,txt):
		log(self.pg.site,"ParamGroup "+self.pg.name+": "+txt)

	def env_factor_one(self, temp,wind,sun):
		p=4 # power factor, favoring nearest-neighbor

		q=Q()
		q &= Q(temp__isnull=(temp is None))
		q &= Q(wind__isnull=(wind is None))
		q &= Q(sun__isnull=(sun is None))

		sum_f = 0
		sum_w = 0
		for ef in self.pg.environment_effects.filter(q):
			d=0
			if temp is not None:
				d += (temp-ef.temp)**2
			if wind is not None:
				d += (wind-ef.wind)**2
			if sun is not None:
				d += (sun-ef.sun)**2
			d = d**(p*0.5)
			if d < 0.001: # close enough
				return ef.factor
			sum_f += ef.factor/d
			sum_w += 1/d
		if sum_w:
			sum_f /= sum_w
		return sum_f


	def env_factor(self,e):
		"""Calculate a weighted factor based on the given environmental parameters"""
		# These weighing 
		ql=(
			(10,e.temp,e.wind,e.sun),
			(4,None  ,e.wind,e.sun),
			(4,e.temp,None  ,e.sun),
			(4,e.temp,e.wind,None ),
			(1,e.temp,None  ,None ),
			(1,None  ,e.wind,None ),
			(1,None  ,None  ,e.sun),
			)
		sum_f = 0
		sum_w = 0
		for weight,temp,wind,sun in ql:
			f = self.env_factor_one(temp,wind,sun)
			if f is not None:
				sum_f += f*weight
				sum_w += weight
		if sum_w:
			sum_f /= sum_w
		return sum_f

class SchedSite(SchedCommon):
	"""Mirrors a site"""
	rain_timer = None
	rain_counter = 0
	_run_delay = None
	_sched = None
	_sched_running = None

	def __new__(cls,s):
		if s.id in sites:
			return sites[s.id]
		self = object.__new__(cls)
		sites[s.id] = self
		self.s = s
		self.connect()

		self.controllers = set()
		self.meters = {}
		for M in METERS:
			ml = set()
			self.meters[M.meter_type] = ml
			for d in getattr(self.s,M.meter_type+"_meters",()).all():
				ml.add(M(d))

		self.log("Startup")
		self.connect_monitors(do_controllers=False)
		return self
	def __init__(self,s):
		pass

	def check_flow(self,**k):
		for c in self.controllers:
			c.check_flow(**k)

	def connect(self):
		self.ci = rpyc.connect(host=self.s.host, port=int(self.s.port), ipv6=True, service=RestartService)

	def maybe_restart(self):
		self.log("reconnecting")
		try:
			self.connect()
		except Exception:
			print_exc()
			gevent.spawn_later(100,self.maybe_restart)
		else:
			self.connect_monitors()

	def connect_monitors(self,do_controllers=True):
		if self.ci is None:
			return
		if do_controllers:
			for c in self.controllers:
				c.connect_monitors()
		for mm in self.meters.itervalues():
			for m in mm:
				m.connect_monitors()
		self.ckf = self.ci.root.monitor(self.check_flow,"check","flow","all")

	def run_schedule(self):
		for c in self.controllers:
			c.run_schedule()

	def refresh(self):
		self.s.refresh()
		for c in self.controllers:
			c.refresh()
		for mm in self.meters.itervalues():
			for m in mm:
				m.refresh()

	def log(self,txt):
		log(self.s,txt)

	def add_controller(self,controller):
		self.controllers.add(controller)

	def no_rain(self):
		"""Rain has stopped."""
		# called by timer
		self.rain_timer = None
		self.log("Stopped raining")
		self.run_main_task()

	def has_rain(self):
		"""Some monitor told us that it started raining"""
		r,self.rain_timer = self.rain_timer,gevent.spawn_later(self.s.db_rain_delay,self.no_rain)
		if r:
			r.kill()
			return
		self.log("Started raining")
		self.rain = True

		n=now()
		#for v in self.s.valves.all():
		for v in Valve.objects.filter(controller__site=self.s):
			valve = SchedValve(v)
			if valve.locked:
				continue
			if v.runoff == 0:
				continue # not affected by rain
			try:
				self.ci.root.command("set","output","off",*(v.var.split()))
			except Exception:
				self.log_error(v)
			v.schedules.filter(start__gte=n).delete()
			for sc in v.schedules.filter(start__gte=now()-timedelta(1),seen=True):
				if sc.start+sc.duration > n:
					sc.duration=n-sc.start
					sc.save()
		self.run_main_task()

	def run_every(self,delay):
		"""Initiate running the calculation and scheduling loop every @delay seconds."""

		if self._run_delay is not None:
			self._run_delay = delay # just update
			return
		self._run_delay = delay
		self._run_last = now()
		self._running = Semaphore()
		self._run_result = None
		self._run = gevent.spawn_later(self._run_delay.total_seconds(), self.run_main_task, kill=False)
		self._sched = gevent.spawn_later(2, self.run_sched_task)

	def run_main_task(self, kill=True):
		"""Run the calculation loop."""
		print >>sys.stderr,"MainTask"
		res = None
		if not self._running.acquire(blocking=False):
			return self._run_result.get()
		try:
			self._run_result = AsyncResult()
			if kill:
				self._run.kill()
			n = now()
			ts = (n-self._run_last).total_seconds()
			if ts < 5:
				try:
					res = self.s.history.order_by("-time")[0]
				except IndexError:
					return None
				else:
					return res
			self._run_last = n

			res = self.main_task()
			return res
		finally:
			self._run = gevent.spawn_later((self._run_last+self._run_delay-n).total_seconds(), self.run_main_task, kill=False)
			r,self._run_result = self._run_result,None
			self._running.release()
			r.set(res)

	def current_history_entry(self):
		# assure that the last history entry is reasonably current
		try:
			he = self.s.history.order_by("-time")[0]
		except IndexError:
			pass
		else:
			if (now()-he.time).total_seconds() < 15:
				return he
		return self.new_history_entry()

	def new_history_entry(self,rain=0):
		"""Create a new history entry"""
		values = {}
		for t,ml in self.meters.items():
			sum_it = False
			sum_val = 0
			sum_f = 0
			for m in ml:
				f = m.weight
				v = m.get_value()
				if v is not None:
					sum_val += f*v
					sum_f += f
				if m.sum_it: sum_it = True
			if sum_f:
				if not sum_it:
					sum_val /= sum_f
				values[t] = sum_val
		
		print >>sys.stderr,"Values:",values
		h = History(site=self.s,time=now(),**values)
		h.save()
		return h

	def sync_history(self):
		for c in self.controllers:
			c.sync_history()

	@transaction.commit_on_success
	def main_task(self):
		self.refresh()
		h = self.new_history_entry()
		self.sync_history()
			
		gevent.spawn_later(2,self.sched_task)
		return h

	def run_sched_task(self,delayed=False):
		if self._sched_running is not None:
			return self._sched_running.get()
		if delayed:
			self._sched = gevent.spawn_later(10,self.run_sched_task)
			return
		self._sched_running = AsyncResult()
		try:
			self.sched_task()
		except Exception:
			self.log(format_exc())
		finally:
			r,self._sched_running = self._sched_running,None
			self._sched = gevent.spawn_later(600,self.run_sched_task)
			r.set(None)

	@transaction.commit_on_success
	def sched_task(self, kill=True):
		self.run_schedule()


class SchedController(SchedCommon):
	"""Mirrors a controller"""

	def __new__(cls,c):
		if c.id in controllers:
			return controllers[c.id]
		self = object.__new__(cls)
		controllers[c.id] = self
		self.c = c
		self.site = SchedSite(self.c.site)
		self.site.add_controller(self)
		return self
	def __init__(self,c):
		pass
	
	def log(self,txt):
		log(self.c,txt)
	
	def sync_history(self):
		for v in self.c.valves.all():
			SchedValve(v).sync_history()

	def run_schedule(self):
		for v in self.c.valves.all():
			SchedValve(v).run_schedule()

	def refresh(self):
		self.c.refresh()
		for v in self.c.valves.all():
			SchedValve(v).refresh()

	def connect_monitors(self):
		if self.site.ci is None:
			return
		for v in self.c.valves.all():
			SchedValve(v).connect_monitors()
		self.ckf = self.site.ci.root.monitor(self.check_flow,"check","flow",*self.c.name.split())

	def check_flow(self,**k):
		for v in self.c.valves.all():
			SchedValve(v).check_flow(**k)

class SchedValve(SchedCommon):
	"""Mirrors a valve."""
	locked = False # external command, don't change
	sched_ts = None
	sched_job = None
	on = False
	flow = 0
	_flow_check = None

	def __new__(cls,v):
		if v.id in valves:
			return valves[v.id]
		self = object.__new__(cls)
		valves[v.id] = self
		self.v = v
		self.site = SchedSite(self.v.controller.site)
		self.params = ParamGroup(self.v.param_group)
		return self
	def __init__(self,v):
		pass

	def _on(self,sched=None,duration=None):
		if duration is None and sched is not None:
			duration = sched.duration
		if duration is None:
			self.log("Run (indefinitely)")
			self.site.ci.root.command("set","output","on",*(self.v.var.split()))
		else:
			self.log("Run for %s"%(duration,))
			self.site.ci.root.command("set","output","on",*(self.v.var.split()), sub=(("for",duration.total_seconds()),"async"))
		if sched is not None:
			sched.seen = True
			sched.save()

	def _off(self):
		self.site.ci.root.command("set","output","off",*(self.v.var.split()))

	def run_schedule(self):
		if self.locked:
			return
		n = now()
		sched = None
		if self.sched_ts is None:
			try:
				sched = self.v.schedules.filter(start__lt=n).order_by("-start")[0]
			except IndexError:
				pass
			else:
				if sched.start+sched.duration > n: # still running
					self._on(sched.start+sched.duration-n)
					self.sched_ts = sched.start+sched.duration
					return
			self.sched_ts = n

		if sched is None:
			try:
				sched = self.v.schedules.filter(start__gte=n).order_by("start")[0]
			except IndexError:
				self._off()
				self.sched_ts = n
				return

		if sched.start > n:
			self._off()
			self.sched_job = gevent.spawn_later((sched.start-n).total_seconds(),s.maybe_restart)
			return
		self._on(self.duration)

	def add_flow(self, val):
		self.flow += val
		if self._flow_check is not None:
			self._flow_check.add_flow(val)

	def check_flow(self,**k):
		cf = None
		try:
			cf = FlowCheck(self)
			# Safety timer
			timer = gevent.spawn_later(self.feed.d.db_max_flow_wait,cf.dead)

			cf.start()
			res = cf.q.get()
			self.log("End flow check: %s"%(res,))
			timer.kill()
		except Exception as ex:
			log_error(self.v)
			if cf is not None:
				cf._unlock()
		
	def refresh(self):
		self.v.refresh()
#		if self.sched is not None:
#			self.sched.refresh()

	def connect_monitors(self):
		if self.site.ci is None:
			return
		print >>sys.stderr," ".join(("Connect to","output","set","*","*")+tuple(self.v.var.split()))
		self.mon = self.site.ci.root.monitor(self.watch_state,"output","set","*","*",*(self.v.var.split()))
		self.ckf = self.site.ci.root.monitor(self.check_flow,"check","flow",*self.v.var.split())
		
	def watch_state(self,event=None,**k):
		"""output set OLD NEW NAME"""
		on = (str(event[3]).lower() in ("1","true","on"))
		if self._flow_check is not None:
			print >>sys.stderr,self.__class__.__name__,self.v.name,event," FLOWCHECK"
			# TODO
			self.on = on
			self._flow_check.state(on)
			return
		if self.locked:
			print >>sys.stderr,self.__class__.__name__,self.v.name,event," LOCKED"
			self.on = on
			return
		try:
			print >>sys.stderr,self.__class__.__name__,self.v.name,event
			if on != self.on:
				self.new_level_entry(self.flow)
				self.on = on
				self.flow = flow

		except Exception:
			print_exc()

	def sync_history(self):
		n=now()
		if (n-self.v.time).total_seconds() > 3500:
			self.new_level_entry()

	def new_level_entry(self,flow=0):
		self.site.current_history_entry()
		n=now()
		hts = None
		try:
			lv = self.v.levels.order_by("-time")[0]
		except IndexError:
			ts = n-timedelta(1,0)
		else:
			ts = lv.time
		sum_f = 0
		sum_r = 0
		for h in self.site.history.filter(time__gt=ts).order_by("time"):
			f = self.params.env_factor(h)
			sum_f += self.site.s._rate*self.params.pg.factor*f*(h.time-ts).totalseconds()
			sum_r += self.v.runoff*h.rain/self.v.area*(h.time-ts).totalseconds()
			ts=h.time

		self.v.level += sum_f
		if flow > 0 and self.v.level > self.v.max_level:
			self.v.level = self.v.max_level
		self.v.level -= flow/self.v.area
		if self.v.level < 0:
			self.log("Level %s ?!?"%(self.v.level,))
			self.v.level = 0
		self.v.time = ts
		lv = Level(valve=self.v,time=ts,level=self.v.level,flow=flow)
		lv.save()
		self.v.save()

	def log(self,txt):
		log(self.v,txt)
	
class FlowCheck(object):
	"""Discover the flow of a valve"""
	q = None
	nflow = 0
	flow = 0
	start = None
	res = None
	def __init__(self,valve):
		self.valve = valve

	def start(self):
		print >>sys.stderr,"_start"
		"""Start flow checking"""
		if self.q is not None:
			raise RuntimeError("already flow checking: "+repr(self.valve))
		if self.valve.feed is None:
			raise RuntimeError("no feed known: "+repr(self.valve))
		if not self.valve.feed.d.var:
			raise RuntimeError("No flow meter: "+repr(self.valve))
		self.q = AsyncResult()
		self.locked = set()
		self.valve._flow_check = self
		for valve in self.valve.feed.valves:
			if valve.locked:
				self._unlock()
				raise RuntimeError("already locked: "+repr(valve))
			valve.locked = True
			self.locked.add(valve)
		self.valve._on()
		print >>sys.stderr,"_start done"
			
	def state(self,on):
		if on:
			self.valve.log("Start flow check")
		else:
			self._unlock()

	def add_flow(self,val):
		self.nflow += 1
		if self.nflow == 2:
			self.start = now()
		if self.nflow > 2:
			self.flow += val
		if self.nflow == 9:
			self.stop()

	def stop(self):
		n=now()
		sec = (n-self.start).total_seconds()
		if sec > 3:
			self.res = self.flow/sec
			self.valve.v.flow = self.res
			self.valve.v.save()
		else:
			self.valve.log("Flow check broken: sec %s"%(sec,))
		if self.valve.on:
			self.valve._off()
		self._unlock()

	def dead(self):
		print >>sys.stderr,"_dead"
		if self.valve._flow_check is not self:
			return
		self.valve.log("Flow check aborted")
		self._unlock()
		
	def _unlock(self):
		print >>sys.stderr,"_unlock"
		if self.valve._flow_check is not self:
			return
		self.valve._flow_check = None
		if self.valve.on:
			self.valve._off()
		for valve in self.locked:
			valve.locked = False
		self.q.set(self.res)
		

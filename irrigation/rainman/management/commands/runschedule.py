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
from operator import attrgetter
import sys,signal
import gevent,rpyc
from functools import partial
from gevent.queue import Queue,Empty
from gevent.coros import Semaphore
from gevent.event import AsyncResult
from rpyc.core.service import VoidService
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller,History,Level
from rainman.utils import now
from rainman.logging import log,log_error
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.db import transaction


### database stuff
### This does not actually work because of transaction-vs.-thread issues
def save_objs(objs):
	for o in objs:
		o.save()

_save_q = Queue()
def _save_job():
	while True:
		s = set()
		o = _save_q.get()
		print >>sys.stderr,"AddSave1",id(o),o
		s.add(o)
		try:
			while True:
				o = _save_q.get(timeout=1)
				if o is None:
					break
				s.add(o)
		except Empty:
			pass

		print >>sys.stderr,"Save",s
		for i in range(3):
			try:
				save_objs(s)
			except Exception:
				print_exc()
			else:
				break
		print >>sys.stderr,"SaveDone"
				

def Save(obj):
	#_save_q.put(obj)
	if obj is not None:
		obj.save()

class NotConnected(RuntimeError):
	pass
class TooManyOn(RuntimeError):
	def __init__(self,valve):
		self.valve = valve
	def __str__(self):
		return u"‹%s: %s / %s: too many open valves›" % (self.__class__.__name__,self.valve.v.controller,self.valve.v)

class Command(BaseCommand):
	args = 'site'
	help = 'Run the current schedule, watch for rain, etc.'

	option_list = BaseCommand.option_list + (
		make_option('-t','--timeout',
			action='store',type='int',
			dest='timeout',
			default=600,
			help='Run main processing loop every N seconds'),
		)

	def handle(self, *args, **options):
		if len(args) != 1:
			print "Choose a site:"
			for s in Site.objects.all():
				print s.name
			sys.exit(1)
		s = Site.objects.get(name=args[0])
		for c in s.controllers.all():
			controller = SchedController(c)
			controller.connect_monitors()

		site = SchedSite(c.site)
		site.run_every(timedelta(0,options['timeout']))
		site.run_sched_task(True,reason="Command")

		if not controllers:
			raise RuntimeError("No controllers for site '%s' found." % (s.name,))
		gevent.spawn(_save_job)
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
			val = float(event[2])
			self.add_value(val)
		except Exception:
			print_exc()

	def refresh(self):
		self.d.refresh()

	def shutdown(self):
		pass

	def sync(self):
		pass

	def connect_monitors(self):
		if not self.d.var:
			return
		if self.site.ci is None:
			return
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
	_flow_check = None

	def __init__(self,*a,**k):
		super(FeedMeter,self).__init__(*a,**k)
		self.valves = set()
		for v in self.d.valves.all():
			valve = SchedValve(v)
			valve.feed = self
			self.valves.add(valve)

	def shutdown(self):
		super(FeedMeter,self).shutdown()
		if self._flow_check is not None:
			self._flow_check.dead()

	def check_max_flow(self,**k):
		if self._flow_check:
			raise RuntimeError("already working")
		try:
			cf = MaxFlowCheck(self)
			# Safety timer
			timer = gevent.spawn_later(self.d.db_max_flow_wait,cf.dead)

			cf.start()
			res = cf.q.get()
			self.log("End flow check: %s"%(res,))
			timer.kill()
		except Exception as ex:
			print_exc()
			try:
				log_error(self.d.site)
				if cf is not None:
					cf._unlock()
			except:
				print_exc()
				raise
		
		
	def add_value(self,val):
		super(FeedMeter,self).add_value(val)
		if self._flow_check:
			self._flow_check.add_flow(val)

		sum_f = 0
		for valve in self.valves:
			if valve.on:
				sum_f += valve.v.flow
		if sum_f:
			# TODO: calculate flow/sec. If greater than the max flow through
			# the valves, the excess must be accounted for someplace else.
			for valve in self.valves:
				if valve.on:
					valve.add_flow(val * valve.v.flow / sum_f)

	def check_flow(self,**k):
		for valve in self.valves:
			valve.check_flow(**k)

	def connect_monitors(self):
		super(FeedMeter,self).connect_monitors()
		if self.d.var:
			self.chk = self.site.ci.root.monitor(self.check_flow,"check","flow",*(self.d.var.split()))
			self.chm = self.site.ci.root.monitor(self.check_max_flow,"check","maxflow",*(self.d.var.split()))

	
		
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
	env_cache = None

	def __new__(cls,pargroup):
		if pargroup.id in paramgroups:
			return paramgroups[pargroup.id]
		self = object.__new__(cls)
		self.env_cache = {}

		paramgroups[pargroup.id] = self
		self.pg = pargroup
		SchedSite(self.pg.site).paramgroups.add(self)
		return self
	def __init__(self,pargroup):
		pass

	def log(self,txt):
		log(self.pg.site,"ParamGroup "+self.pg.name+": "+txt)

	def sync(self):
		pass
	def refresh(self):
		self.pg.refresh()
		self.env_cache = {}
	def shutdown(self):
		pass

	def env_factor(self,h,logger):
		return self.pg.env_factor(h,logger)

class SchedSite(SchedCommon):
	"""Mirrors a site"""
	rain_timer = None
	rain_counter = 0
	_run_delay = None
	_sched = None
	_sched_running = None
	_delay_on = None
	running = False

	def __new__(cls,s):
		if s.id in sites:
			return sites[s.id]
		self = object.__new__(cls)
		sites[s.id] = self
		self.s = s
		self.connect()
		self._delay_on = Semaphore()

		self.controllers = set()
		self.paramgroups = set()
		self.meters = {}
		for M in METERS:
			ml = set()
			self.meters[M.meter_type] = ml
			for d in getattr(self.s,M.meter_type+"_meters").all():
				ml.add(M(d))

		self.log("Startup")
		self.connect_monitors(do_controllers=False)
		signal.signal(signal.SIGINT,self.do_shutdown)
		signal.signal(signal.SIGTERM,self.do_shutdown)
		signal.signal(signal.SIGHUP,self.do_syncsched)

		self.running = True
		return self
	def __init__(self,s):
		pass

	def do_shutdown(self,x,y,**k):
		gevent.spawn_later(0.1,self.shutdown)

	def do_syncsched(self,x,y):
		gevent.spawn_later(0.1,self.syncsched)

	def syncsched(self):
		print >>sys.stderr,"Sync+Sched"
		self.sync()
		self.refresh()
		self.run_sched_task(reason="Sync+Sched")

	def delay_on(self):
		self._delay_on.acquire()
		gevent.spawn_later(1,self._delay_on.release)

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
		self.ckf = self.ci.root.monitor(self.check_flow,"check","flow",*self.s.var.split(" "))
		self.cks = self.ci.root.monitor(partial(self.run_sched_task,reason="read schedule"),"read","schedule",*self.s.var.split(" "))
		self.ckt = self.ci.root.monitor(self.sync,"sync",*self.s.var.split(" "))
		self.cku = self.ci.root.monitor(self.do_shutdown,"shutdown",*self.s.var.split(" "))

	def sync(self,**k):
		print >>sys.stderr,"Sync"
		for c in self.controllers:
			c.sync()
		for pg in self.paramgroups:
			pg.sync()
		for mm in self.meters.itervalues():
			for m in mm:
				m.sync()
		self.run_main_task()
		Save(None)
		print >>sys.stderr,"Sync end"
	
	def shutdown(self,**k):
		print >>sys.stderr,"Shutdown"
		signal.signal(signal.SIGINT,signal.SIG_DFL)
		signal.signal(signal.SIGTERM,signal.SIG_DFL)
		if self.running:
			self.running = False
			self.sync()
			for pg in self.paramgroups:
				pg.sync()
			for c in self.controllers:
				c.shutdown()
			for mm in self.meters.itervalues():
				for m in mm:
					m.shutdown()
		Save(None)
		sys.exit(0)


	def run_schedule(self):
		for c in self.controllers:
			c.run_schedule()

	def refresh(self):
		self.s.refresh()
		for pg in self.paramgroups:
			pg.refresh()
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
		for v in Valve.objects.filter(controller__site=self.s, runoff__gt=0):
			valve = SchedValve(v)
			if valve.locked:
				continue
			try:
				self.send_command("set","output","off",*(v.var.split()))
			except NotConnected:
				pass
			except Exception:
				self.log_error(v)
			v.schedules.filter(start__gte=n).delete()
			for sc in v.schedules.filter(start__gte=n-timedelta(1),start__lt=n,seen=True):
				if sc.start+sc.duration > n:
					sc.duration=n-sc.start
					Save(sc)
			v.schedules.filter(start__gte=n-timedelta(1),seen=False).delete()
		self.run_main_task()

	def send_command(self,*a,**k):
		# TODO: return a sensible error and handle that correctly
		if self.ci is None:
			raise NotConnected
		self.ci.root.command(*a,**k)

	def run_every(self,delay):
		"""Initiate running the calculation and scheduling loop every @delay seconds."""

		if self._run_delay is not None:
			self._run_delay = delay # just update
			return
		self._run_delay = delay
		self._run_last = now()
		self._running = Semaphore()
		self._run_result = None
		sd = self._run_delay.total_seconds()/10
		if sd < 66: sd = 66
		self._run = gevent.spawn_later(sd, self.run_main_task, kill=False)
		if self._sched is not None:
			self._sched.kill()
		self._sched = gevent.spawn_later(2, self.run_sched_task, kill=False, reason="run_every")

	def run_main_task(self, kill=True):
		"""Run the calculation loop."""
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

	def current_history_entry(self,delta=15):
		# assure that the last history entry is reasonably current
		try:
			he = self.s.history.order_by("-time")[0]
		except IndexError:
			pass
		else:
			if (now()-he.time).total_seconds() < delta:
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
		Save(h)
		return h

	def sync_history(self):
		for c in self.controllers:
			c.sync_history()

	def main_task(self):
		print >>sys.stderr,"MainTask"
		self.refresh()
		h = self.current_history_entry(3)
		self.sync_history()
			
		gevent.spawn_later(2,self.sched_task)
		print >>sys.stderr,"MainTask end",h
		return h

	def run_sched_task(self,delayed=False,reason=None,kill=True, **k):
		print >>sys.stderr,"RunSched",reason
		if self._sched_running is not None:
			return self._sched_running.get()
		if self._sched is not None:
			if kill:
				self._sched.kill()
		if delayed:
			self._sched = gevent.spawn_later(10,self.run_sched_task,kill=False,reason="Timer 10")
			return
		self._sched = None
		self._sched_running = AsyncResult()
		try:
			self.sched_task()
		except Exception:
			self.log(format_exc())
		finally:
			r,self._sched_running = self._sched_running,None
			if self._sched is None:
				self._sched = gevent.spawn_later(600,self.run_sched_task,kill=False,reason="Timer 600")
			r.set(None)
		print >>sys.stderr,"RunSched end"

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
	
	def sync(self):
		for v in self.c.valves.all():
			SchedValve(v).sync()
		
	def sync_history(self):
		for v in self.c.valves.all():
			SchedValve(v).sync_history()

	def run_schedule(self):
		for v in self.c.valves.all():
			SchedValve(v).run_schedule()

	def shutdown(self):
		for v in self.c.valves.all():
			SchedValve(v).shutdown()

	def refresh(self):
		self.c.refresh()
		for v in self.c.valves.all():
			SchedValve(v).refresh()

	def connect_monitors(self):
		if self.site.ci is None:
			return
		for v in self.c.valves.all():
			SchedValve(v).connect_monitors()
		self.ckf = self.site.ci.root.monitor(self.check_flow,"check","flow",*self.c.var.split())

	def check_flow(self,**k):
		for v in self.c.valves.all():
			SchedValve(v).check_flow(**k)

	def has_max_on(self):
		if not self.c.max_on:
			return False
		n=0
		for v in self.c.valves.all():
			if SchedValve(v).on:
				n += 1
		return n >= self.c.max_on

class SchedValve(SchedCommon):
	"""Mirrors a valve."""
	locked = False # external command, don't change
	sched = None
	sched_ts = None
	sched_job = None
	sched_lock = None
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
		self.controller = SchedController(self.v.controller)
		self.sched_lock = Semaphore()
		if self.site.ci:
			try:
				self.site.send_command("set","output","off",*(self.v.var.split()))
			except NotConnected:
				pass
		return self
	def __init__(self,v):
		pass

	def _on(self,sched=None,duration=None):
		print >>sys.stderr,"Open",self.v.var
		self.site.delay_on()
		if self.controller.has_max_on():
			print >>sys.stderr,"… but too many:", " ".join(str(v) for v in self.c.valves.all() if SchedValve(v).on)
			raise TooManyOn(self)
		if duration is None and sched is not None:
			duration = sched.duration
		if duration is None:
			self.log("Run (indefinitely)")
			self.site.send_command("set","output","on",*(self.v.var.split()))
		else:
			self.log("Run for %s"%(duration,))
			self.site.send_command("set","output","on",*(self.v.var.split()), sub=(("for",duration.total_seconds()),("async",)))
		if sched is not None:
			if self.v.verbose:
				self.log("Opened for %s"%(sched,))
			self.sched = sched
			if not sched.seen:
				sched.start = now()
				sched.seen = True
			Save(sched)
		else:
			if self.v.verbose:
				self.log("Opened for %s"(duration,))

	def _off(self):
		if self.on:
			if self.v.verbose:
				self.log("Closing")
			print >>sys.stderr,"Close",self.v.var
		try:
			self.site.send_command("set","output","off",*(self.v.var.split()))
		except NotConnected:
			pass

	def shutdown(self):
		if self._flow_check is not None:
			self._flow_check.dead()

	def run_schedule(self):
		if not self.sched_lock.acquire(blocking=False):
			return
		try:
			self._run_schedule()
		except Exception:
			self.log(format_exc())
		finally:
			self.sched_lock.release()

	def _run_schedule(self):
		if self.sched_job is not None:
			self.sched_job.kill()
			self.sched_job = None
		if self.locked:
			return
		n = now()

		if self.sched is not None:
			self.sched.refresh()
			if self.sched.start+self.sched.duration <= n:
				self._off()
				self.sched_ts = self.sched.start+self.sched.duration
				self.sched = None
			else:
				self.sched_job = gevent.spawn_later((self.sched.start+self.sched.duration-n).total_seconds(),self.run_sched_task,reason="_run_schedule 1")
			return

		sched = None
		if self.sched_ts is None:
			try:
				sched = self.v.schedules.filter(start__lt=n).order_by("-start")[0]
			except IndexError:
				self.sched_ts = n
			else:
				self.sched_ts = sched.start+sched.duration
				if sched.start+sched.duration > n: # still running
					try:
						self._on(sched, sched.start+sched.duration-n)
					except TooManyOn:
						self.log("Could not schedule: too many open valves")
					except NotConnected:
						self.log("Could not schedule: connection to HomEvenT failed")
					return

		try:
			sched = self.v.schedules.filter(start__gte=self.sched_ts).order_by("start")[0]
		except IndexError:
			self._off()
			self.sched_ts = n
			return

		if sched.start > n:
			self._off()
			self.sched_job = gevent.spawn_later((sched.start-n).total_seconds(),self.run_sched_task,reason="_run_schedule 2")
			return
		try:
			self._on(sched)
		except TooManyOn:
			self.log("Could not schedule: too many open valves")
		except NotConnected:
			self.log("Could not schedule: connection to HomEvenT failed")
	
	def run_sched_task(self,reason="valve"):
		self.sched_job = None
		self.site.run_sched_task(reason=reason)

	def add_flow(self, val):
		self.flow += val
		if self._flow_check is not None:
			self._flow_check.add_flow(val)

	def check_flow(self,**k):
		cf = None
		try:
			cf = FlowCheck(self)
			cf.run()
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
		self.mon = self.site.ci.root.monitor(self.watch_state,"output","set","*","*",*(self.v.var.split()))
		self.ckf = self.site.ci.root.monitor(self.check_flow,"check","flow",*self.v.var.split())
		
	def watch_state(self,event=None,**k):
		"""output set OLD NEW NAME"""
		on = (str(event[3]).lower() in ("1","true","on"))
		if self._flow_check is not None:
			# TODO
			self.on = on
			self._flow_check.state(on)
			return
		if self.locked:
			self.on = on
			return
		try:
			if on != self.on:
				flow,self.flow = self.flow,0
				self.new_level_entry(flow)
				self.on = on

		except Exception:
			print_exc()

	def sync(self):
		flow,self.flow = self.flow,0
		self.new_level_entry(flow)

	def sync_history(self):
		n=now()
		try:
			lv = self.v.levels.order_by("-time")[0]
		except IndexError:
			pass
		else:
			if self.v.time > lv.time:
				self.log("Timestamp downdate: %s %s" % (self.v.time,lv.time))
				self.v.time = lv.time
				Save(self.v)
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
		for h in self.site.s.history.filter(time__gt=ts).order_by("time"):
			if self.v.verbose>2:
				self.log("Env factor for %s: T=%s W=%s S=%s"%(h,h.temp,h.wind,h.sun))
			f = self.params.env_factor(h, logger=self.log if self.v.verbose>2 else None)
			if self.v.verbose>1:
				self.log("Env factor for %s is %s"%(h,f))
			sum_f += self.v.shade*self.site.s.db_rate*self.params.pg.factor*f*(h.time-ts).total_seconds()
			sum_r += self.v.runoff*h.rain
			ts=h.time

		if self.v.verbose:
			self.log("Apply env %f, rain %r"%(sum_f,sum_r))

		if self.v.time == ts:
			return
		if self.v.level < 0:
			self.v.level = 0
		self.v.level += sum_f
		if flow > 0 and self.v.level > self.v.max_level:
			self.v.level = self.v.max_level
		self.v.level -= flow/self.v.area+sum_r
		if self.v.level < 0:
			self.log("Level %s ?!?"%(self.v.level,))
		self.v.time = ts
		lv = Level(valve=self.v,time=ts,level=self.v.level,flow=flow)
		Save(lv)
		Save(self.v)

	def log(self,txt):
		log(self.v,txt)
	
class FlowCheck(object):
	"""Discover the flow of a valve"""
	q = None
	nflow = 0
	flow = 0
	start = None
	res = None
	timer = None
	def __init__(self,valve):
		self.valve = valve

	def start(self):
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
		try:
			self.valve._on(duration=self.valve.feed.d.max_flow_wait)
		except NotConnected:
			self._unlock()
			raise
			
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
			Save(self.valve.v)
		else:
			self.valve.log("Flow check broken: sec %s"%(sec,))
		if self.valve.on:
			self.valve._off()
		self._unlock()

	def dead(self, kill=True):
		if self.timer is not None:
			if kill:
				self.timer.kill()
			self.timer = None
		if self.valve._flow_check is not self:
			return
		self.valve.log("Flow check aborted")
		self._unlock()
		
	def _unlock(self):
		if self.timer is not None:
			self.timer.kill()
			self.timer = None
		if self.valve._flow_check is not self:
			return
		self.valve._flow_check = None
		if self.valve.on:
			self.valve._off()
		for valve in self.locked:
			valve.locked = False
		self.q.set(self.res)

	def run(self):
		# Safety timer
		self.timer = gevent.spawn_later(self.valve.feed.d.db_max_flow_wait, self.dead, kill=False)

		self.start()
		res = self.q.get()
		self.valve.log("End flow check: %s"%(res,))

		
class MaxFlowCheck(object):
	"""Discover the flow of a feed"""
	q = None
	nflow = 0
	flow = 0
	start = None
	res = None
	timer = None
	def __init__(self,feed):
		self.feed = feed

	def start(self):
		"""Start flow checking"""
		if self.q is not None:
			raise RuntimeError("already flow checking: "+repr(self.valve))
		if not self.feed.d.var:
			raise RuntimeError("No flow meter: "+repr(self.valve))
		self.q = AsyncResult()
		self.locked = set()
		self.on = set()
		self.feed._flow_check = self
		for valve in self.feed.valves:
			if valve.locked:
				self._unlock()
				raise RuntimeError("already locked: "+repr(valve))
			valve.locked = True
			self.locked.add(valve)

		valves = sorted(self.feed.valves, reverse=True, key=attrgetter('v.flow'))
		for valve in valves:
			try:
				valve._on(duration=self.feed.d.max_flow_wait)
			except TooManyOn:
				pass
			else:
				self.on.add(valve)
			
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
			self.feed.d.flow = self.res
			Save(self.feed.d)
		else:
			self.feed.log("Flow check broken: sec %s"%(sec,))
		self._unlock()

	def dead(self,kill=True):
		if self.timer is not None:
			if kill:
				self.timer.kill()
			self.timer = None
		if self.feed._flow_check is not self:
			return
		self.feed.log("Flow check aborted")
		self._unlock()
		
	def _unlock(self):
		if self.timer is not None:
			self.timer.kill()
			self.timer = None
		if self.feed._flow_check is not self:
			return
		self.feed._flow_check = None
		for valve in self.on:
			valve._off()
		for valve in self.locked:
			valve.locked = False
		self.q.set(self.res)
		
	def run(self):
		# Safety timer
		self.timer = gevent.spawn_later(self.feed.d.db_max_flow_wait,cf.dead,False)

		self.start()
		res = self.q.get()
		self.feed.site.log("End flow check: %s"%(res,))


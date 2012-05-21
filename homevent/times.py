# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division

"""\
This code does some standard time handling.

"""

import datetime as dt
from time import time,mktime
from calendar import isleap,monthrange

import gevent
from gevent.queue import Queue

from homevent import TESTING

startup = dt.datetime.now()

if TESTING:
	SLOT=20
	current_slot = 0
	def now(force=False):
		if force:
			return dt.datetime.now()
		r = dt.datetime.utcfromtimestamp(1049522828) # 2003-04-05 06:07:08 UTC
		return r + dt.timedelta(0, current_slot // SLOT, (current_slot % SLOT) * (1e6 / SLOT) )

	def test_runtime():
		return current_slot / SLOT

	def slot_update(tm):
		"""Update the time slot until the given time is reached"""
		if isinstance(tm,dt.datetime):
			td = unixdelta(tm - now())
		else:
			td = tm - unixtime(now())
		if td < 0:
			return

		# Do not increase by more than one, because another greenlet (one
		# which requires shrter timeouts) might run in parallel 
		global current_slot
		current_slot += 1

	def sleep(force,timeout):
		from homevent.twist import log_wait,callLater
		with log_wait("%s timer wait for %s" % ("Forced" if force else "Fake", timeout)):
			if force:
				gevent.sleep(timeout)
				return
			q = Queue()
			callLater(False,timeout,q.put,None)
			q.get()

else:
	def now(force=False):
		return dt.datetime.now()
	def test_runtime():
		raise RuntimeError("We are not testing!")
	def slot_update(tm):
		raise RuntimeError("We are not testing!")
	def sleep(_,timeout):
		with log_wait("Timer wait for %s" % (timeout,)):
			gevent.sleep(timeout)

def unixdelta(delta):
	return delta.days*24*60*60 + delta.seconds + delta.microseconds/1e6;

units = ((24*60*60,"dy"),
         (60*60,"hr"),
		 (60,"min")) # seconds are explicit, below

def humandelta(delta):
	res = ""
	res2= ""
	if isinstance(delta,dt.timedelta):
		if delta.days < 0:
			assert delta.seconds >= 0
			# right now this code only handles positive seconds
			# timedelta(0,-1) => timedelta(-1,24*60*60-1)
			res = "-"
			delta = - delta
		if delta.days > 0:
			res = "%d dy"%(d.days)
		delta = delta.seconds + delta.microseconds / 1e6
	elif delta < 0:
		delta = - delta
		res = "-"
	for lim, name in units:
		if delta > lim:
			res += res2+"%d %s" % (delta // lim, name)
			res2 = " "
			delta %= lim
	if delta > 0.1:
		res += res2+"%3.1f sec" % delta

	if len(res) < 2:
		res = "now"

	return res

def unixtime(tm):
	return mktime(tm.timetuple()) + tm.microsecond / 1e6

def isodate(yr,wk,wdy):
	res = dt.date(yr,1,1)
	_,_,dy = res.isocalendar()
	return res + dt.timedelta(7*(wk-1) + wdy-dy)

def simple_time_delta(w):
	s=0
	m=1
	while w:
		if len(w) == 1:
			pass
		elif w[1] in ("s","sec","second","seconds"):
			w.pop(1)
		elif w[1] in ("m","min","minute","minutes"):
			m = 60
			w.pop(1)
		elif w[1] in ("h","hr","hour","hours"):
			m = 60*60
			w.pop(1)
		elif w[1] in ("d","dy","day","days"):
			m = 60*60*24
			w.pop(1)
		elif w[1] in ("w","wk","week","weeks"):
			m = 60*60*24*7
			w.pop(1)
		elif w[1] in ("m","mo","month","months"):
			m = 60*60*24*30 ## inexact!
			w.pop(1)
		elif w[1] in ("y","yr","year","years"):
			m = 60*60*24*365 ## inexact!
			w.pop(1)
		elif w[1] in ("+","-"):
			pass
		else:
			raise SyntaxError("unknown unit",w[1])
		s += m * w[0]
		w.pop(0)
		if w:
			if w[0] == "+":
				w.pop(0)
				m = 1
			elif w[0] == "-":
				w.pop(0)
				m = -1
			else:
				m = 1 # "1min 59sec"
	return s

def time_delta(args, now=None):
	w = list(args)
	step = None
	if now is None: now = globals()["now"]()
	if not w:
		raise SyntaxError("Empty time delta")

	try:
		sv = float(w[0])
	except (IndexError,ValueError,TypeError):
		pass
	else:
		if sv > 1000000000: # 30 years plus: Forget it, that's a unixtime.
			step = dt.datetime.fromtimestamp(sv)
			w.pop(0)

	s = simple_time_delta(w)
	if not isinstance(now,(int,float)):
		s = dt.timedelta(0,s)
	if step is None:
		now += s
	elif now < step-1:
		now = step + s
	else:
		now += s - (now-step) % s
	return now


class _store(object): pass

def collect_words(n,w):
	p = _store()
	p.h = None
	p.m = None # absolute hour/minute/second
	p.s = None

	p.yr = None
	p.mn = None # absolute year/month/day
	p.dy = None

	p.wk = None
	p.dow = None # week_of_year, weekday, which weekday?
	p.nth = None

	if n is None:
		n = now()
	p.now = n

	weekdays = {
		"monday":0, "tuesday":1, "wednesday":2, "thursday":3, "friday":4, "saturday":5,"sunday":6,
		"mon":0, "tue":1, "wed":2, "thu":3, "fri":4, "sat":5,"sun":6,
		"mo":0, "tu":1, "we":2, "th":3, "fr":4, "sa":5,"su":6,
		}
	f = None

	w = list(w)
	try:
		s = float(w[0])
	except (IndexError,ValueError,TypeError):
		pass
	else:
		if s > 1000000000: # 30 years plus. Forget it, that's a unixtime.
			p.now = dt.datetime.fromtimestamp(s)
			w.pop(0)

	while w:
		if w[0] == "+":
			w.pop(0)
			f = 1
		elif w[0] == "-":
			w.pop(0)
			f = -1
		if w[0] in weekdays:
			assert p.dow is None, "You already specified the day of week"
			assert f is None, "A sign makes no sense here"
			p.dow = weekdays[w.pop(0)]
			p.nth = 0
			continue
		val = int(w.pop(0))
		if f is not None:
			val = f * val
			f = None
		unit = w.pop(0)
		if unit in ("s","sec","second","seconds"):
			assert p.s is None, "You already specified the second"
			assert -60<val<60, "Seconds need to be between 0 and 59"
			p.s = val
		elif unit in ("m","min","minute","minutes"):
			assert p.m is None, "You already specified the minute"
			assert -60<val<60, "Minutes need to be between 0 and 59"
			p.m = val
		elif unit in ("h","hr","hour","hours"):
			assert p.h is None, "You already specified the hour"
			assert -24<val<24, "Hours need to be between 0 and 23"
			p.h = val
		elif unit in ("d","dy","day","days"):
			assert p.dy is None, "You already specified the day"
			assert val != 0 and abs(val) <= 31, "Months only have 31 days max"
			p.dy = val
		elif unit in ("m","mo","month","months"):
			assert p.mn is None, "You already specified the month"
			assert val != 0 and abs(val) <= 12, "Years only have 12 months max"
			p.mn = val
		elif unit in ("y","yr","year","years"):
			assert p.yr is None, "You already specified the year"
			if val > 0 and val < 100:
				val += now.year
			else:
				assert val >= now.year and val < now.year+100, "WHICH year? Sorry, the time machine module is not available."
			p.yr = val
		elif unit in ("w","wk","week","weeks"):
			assert p.wk is None, "You already specified the week-of-year"
			assert val != 0 and abs(val) <= 53, "Years only have 53 weeks max"
			p.wk = val
		elif unit in weekdays:
			assert p.dow is None, "You already specified the day of week"
			assert val != 0 and abs(val) <= 4, "Months have max. 5 of each weekday. (use -1 if you mean the last one)"
			p.dow = weekdays[unit]
			p.nth = val
			continue
		else:
			raise SyntaxError("unknown unit",unit)
	return p

def time_until(args, now=None, invert=False):
	"""\
		Find the next time which is in the future and matches the arguments.
		If "invert" is True, find the next time which does *not*.
		"""
	p = collect_words(now,args)

	p.res = p.now
	
	# Theory of operation:
	# For each step, there are four cases:
    #
	# a- can be left alone
	#    = do nothing
	# b- needs to be increased
	#    = if at the limit, set to start value and increase the next position
	# c- needs to be at one specific value
	#    = if too large, increase the next position; then set.
	# d- (b) AND (c) both
	#    = accomplished by moving the intended value one step back
	#      during the crucial comparison
	# Another complication is that if somebody specifies a month but not
	# a day/hour/whatever, presumably they mean "as soon as that month
	# arrives" and not "that month, same day/hour/minute/second as now".

	def lim12(): return 12
	def lim30(): return monthrange(p.res.year,p.res.month)[1]
	def lim24(): return 23
	def lim60(): return 59

	def check_year(force=False):
		clear_fields={'second':0,'minute':0,'hour':0,'day':1,'month':1}
		# This is simpler, as there's nothing a year is owerflowing into.
		# (I do hope that this won't change any time soon …)
		if p.yr is None:
			if force:
				p.res = p.res.replace(year=p.res.year+1, **clear_fields)
		else:
			p.res = p.res.replace(year=p.yr, **clear_fields)

	def step(sn,ln, beg,lim, nextfn, clear_fields): # shortname, longname, limit
		def next_whatever(force=False):
			goal = getattr(p,sn)
			real = getattr(p.res,ln)
			if goal is None:
				rgoal = real # (a) and (b)
			elif goal < 0:
				rgoal = lim()+goal+1
			else:
				rgoal = goal
			if force:
				rgoal += 1 # (b) and (d)

			if real > rgoal or rgoal > lim(): # needs increasing: (b), maybe (c)/(d)
				h = {ln: beg}
				h.update(clear_fields)
				p.res = p.res.replace(**h)
				nextfn(True)
				force=False
				if rgoal > lim():
					rgoal = beg
			if force or goal is not None:
				if real != rgoal: # otherwise we clear fields for no reason
					h = {ln: rgoal}
					h.update(clear_fields)
					p.res = p.res.replace(**h)
			# … and if the goal is None, this is either (a),
			# or 'our' value has been set to the beginning value, above
		return next_whatever

	check_month = step("mn","month",1,lim12,check_year,{'second':0,'minute':0,'hour':0,'day':1})
	check_day   = step("dy","day",1,lim30,check_month,{'second':0,'minute':0,'hour':0})
	check_hour  = step("h","hour",0,lim24,check_day,{'second':0,'minute':0})
	check_min   = step("m","minute",0,lim60,check_hour,{'second':0})
	check_sec   = step("s","second",0,lim60,check_min,{})
		

	# Intermission: figure out how long until the condition is False
	if invert:
		p.delta = None
		def get_delta(fn, sn=None,ln=None):
			if p.delta is not None and p.delta == p.now: return
			if getattr(p,sn) is None:
				return
			if getattr(p.now,ln) != getattr(p,sn):
				p.delta = p.now
				return
			p.res = p.now
			fn(True)
			d = p.res
			if p.delta is None or p.delta > d: p.delta = d

		get_delta(check_year,"yr","year")
		get_delta(check_month,"mn","month")
		get_delta(check_day,"dy","day")
		if p.delta is not None and p.delta == p.now: return p.now

		get_delta(check_hour,"h","hour")
		get_delta(check_min,"m","minute")
		get_delta(check_sec,"s","second")
		if p.delta is not None and p.delta == p.now: return p.now

		if p.wk is not None: # week of the year
			yr,wk,dow = p.now.isocalendar()
			if p.wk != wk: return p.now
			p.res = p.now
			check_day(True)
			d = p.res + dt.timedelta(7-dow) # until end-of-week
			if p.delta is None or p.delta > d: p.delta = d
		if p.dow is not None:
			yr,wk,dow = p.now.isocalendar()
			dow -= 1 # 1…7 ⇒ 0…6
			if p.dow != dow: return p.now
			p.res = p.now
			check_day(True)
			if p.delta is None or p.delta > p.res: p.delta = p.res
		if p.nth: # may be zero
			p.res = p.now
			if p.nth != nth():
				return p.now

		return p.delta


	# Now here's the fun part: figure out how long until the condition is true
	# first, check absolute values
	check_year (False)
	check_month(False)
	check_day  (False)

	# Next: the weekday-related stuff. We assume, for convenience, that
	# any conflicting specifications simply mean "afterwards".

	# p.wk : week of the year (1…53)
	# p.dow : day of the week (Thursday)
	# p.nth : which day in the week (i.e. 1st Monday)
	def upd(delta):
		if not delta: return
		p.res = p.res + dt.timedelta(delta)
		if p.res > p.now:
			p.res = p.res.replace(hour=0,minute=0,second=0)
		if p.res < p.now:
			p.res = p.now
		
	def nth():
		if p.nth > 0:
			return 1 + ((p.res.day-1) // 7)
		else:
			return -1 - ((lim30()-p.res.day) // 7)

	if p.wk: # week of the year
		yr,wk,dow = p.res.isocalendar()
		if p.wk < wk:
			check_year(True)
			yr,wk,dow = p.res.isocalendar()
		upd(7*(p.wk-wk))
		if p.mn is None and p.dy is None:
			# No month/day specified, so assume that we can go back a bit.
			# (iso day 1 of week 1 of year X may be in December X-1.)
			# … but not into the past, please!
			upd(1-dow)
			if p.res < p.now: p.res = p.now

	if p.dow is not None:
		yr,wk,dow = p.res.isocalendar()
		dow -= 1 # 1…7 ⇒ 0…6
		if p.dow < dow:
			dow -= 7 # next week
		upd(p.dow-dow)

	if p.nth: # may be zero
		if p.nth < nth():
			upd(7*(4+p.nth-nth()))
			# That will take me to the first.
			if p.nth < nth(): # five weekdays in this month!
				upd(7)
				# … except when it doesn't.
		if p.nth > nth():
			upd(7*(p.nth-nth()))
			# Either way, as if by magic, we now get the correct date. 

	check_hour (False)
	check_min  (False)
	check_sec  (False)

	return p.res



#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does some standard time handling.

"""

import datetime as dt
from calendar import isleap,monthrange

def isodate(yr,wk,wdy):
	res = dt.date(yr,1,1)
	_,_,dy = res.isocalendar()
	return res + dt.timedelta(7*(wk-1) + wdy-dy)

def time_delta(args):
	w = list(args)
	s = 0
	if not w:
		raise SyntaxError("Empty time delta")
	m = 1
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
		elif unit in ("y","yr","year","years"):
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

class _store(object): pass

def collect_words(w):
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

	weekdays = {
		"mon":0, "tue":1, "wed":2, "thu":3, "fri":4, "sat":5,"sun":6,
		"mo":0, "tu":1, "we":2, "th":3, "fr":4, "sa":5,"su":6,
		}
	f = None

	w = list(w)
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
			assert val != 0 and abs(val) <= 4, "Months only have 5 days each, max (use -1 if you mean the last one)"
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
	p = collect_words(args)

	if now is None:
		now = dt.datetime()
	p.res = now
	
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
		zero = dt.timedelta(0)
		def get_delta(fn, sn=None,ln=None):
			if p.delta is zero: return
			if getattr(p,sn) is None:
				return
			if getattr(now,ln) != getattr(p,sn):
				p.delta = zero
				return
			p.res = now
			fn(True)
			d = p.res - now
			if p.delta is None or p.delta > d: p.delta = d

		get_delta(check_year,"yr","year")
		get_delta(check_month,"mn","month")
		get_delta(check_day,"dy","day")
		if p.delta is zero: return zero

		get_delta(check_hour,"h","hour")
		get_delta(check_min,"m","minute")
		get_delta(check_sec,"s","second")
		if p.delta is zero: return zero

		if p.wk: # week of the year
			yr,wk,dow = now.isocalendar()
			if p.wk != wk: return zero
			p.res = now
			check_day(True)
			d = p.res - now + dt.timedelta(7-dow) # until end-of-week
			if p.delta is None or p.delta > d: p.delta = d
		if p.dow is not None:
			yr,wk,dow = now.isocalendar()
			dow -= 1 # 1…7 ⇒ 0…6
			if p.dow != dow: return zero
			p.res = now
			check_day(True)
			d = p.res - now
			if p.delta is None or p.delta > d: p.delta = d
		if p.nth: # may be zero
			if p.nth != nth():
				return zero
		return p.delta


	# Now here's the fun part...
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
		if p.res > now:
			p.res = p.res.replace(hour=0,minute=0,second=0)
		if p.res < now:
			p.res = now
		
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
			upd(1-dow)

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

	return p.res - now



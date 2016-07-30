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

"""\
		Calculate valve schedules.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller,History,Level
from rainman.utils import now,str_tz
from rainman.logging import log
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc,get_current_timezone
from optparse import make_option
from time import sleep
from traceback import print_exc
import rpyc
import errno
import sys

n=now()
soon=n+timedelta(0,15*60)
later=n+timedelta(0,2*60*60)

class Command(BaseCommand):
	args = '<valve>…'
	help = 'Generate a schedule'

	option_list = BaseCommand.option_list + (
			make_option('-s','--site',
				action='store',
				dest='site',
				default=None,
				help='Select the site to use'),
			make_option('-c','--controller',
				action='store',
				dest='controller',
				default=None,
				help='Select the controller to use'),
			make_option('-f','--feed',
				action='store',
				dest='feed',
				default=None,
				help='Select the water feed to use'),
			make_option('-a','--age',
				action='store',
				type=float,
				dest='age',
				default=1,
				help='How far into the future to generate the schedule'),
			make_option('-d','--delay',
				action='store',
				type=float,
				dest='delay',
				default=None,
				help='How far into the future to start generating the schedule'),
			make_option('-g','--group',
				action='store',
				dest='group',
				default=None,
				help='Select the group to use'),
			make_option('-n','--no-save',
				action='store_false',
				dest='save',
				default=True,
				help="don't save"),
			make_option('-t','--trigger',
				action='store_true',
				dest='trigger',
				default=False,
				help="trigger an immediate schedule read"),
			make_option('-V','--verbose',
				action='store_true',
				dest='verbose',
				default=False,
				help="be more chatty"),
			)

	def handle(self, *args, **options):
		import pdb;pdb.set_trace()
		if options['trigger']:
			for s in Site.objects.all():
				if not s.var: continue
				try:
					c = rpyc.connect(s.host, int(s.port), ipv6=True)
					c.root.command("trigger","sync",*s.var.split())
					c.close()
				except EnvironmentError as e:
					if e.errno == errno.ECONNREFUSED:
						print("Connecting to '%s' failed" % (s.host,), fiel=sys.stderr)
						continue
					print_exc()
				except Exception:
					print_exc()
				else:
					print("Connecting to '%s' succeeded" % (s.host,), file=sys.stderr)
			sleep(10)
		q = Q()
		if options['site']:
			q &= Q(controller__site__name=options['site'])
		if options['group']:
			q &= Q(groups__name=options['group'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		if options['feed']:
			q &= Q(feed__name=options['feed'])

		global soon
		if options['delay'] is not None:
			delay=float(options['delay'])
		elif options['trigger']:
			delay=1
		else:
			delay=10
		soon=n+timedelta(0,delay*60)

		sites = set()
		if len(args):
			for a in args:
				v = Valve.objects.get(q & Q(name=a))
				if options['trigger']:
					sites.add(v.controller.site)
				self.force_one_valve(v, options)
				self.one_valve(v, options)
		else:
			for v in Valve.objects.filter(q).order_by("level"):
				if options['trigger']:
					sites.add(v.controller.site)
				self.force_one_valve(v,options)
			for v in Valve.objects.filter(q).order_by("level"):
				self.one_valve(v,options)

		if options['trigger']:
			for s in sites:
				c = rpyc.connect(s.host, int(s.port), ipv6=True)
				c.root.command("trigger","read","schedule",*s.var.split())
				c.close()

	def one_valve(self,v,options):
		if v.feed.disabled:
			return
		if (v.level < v.stop_level) if v.priority else (v.level < v.start_level):
			if options['save'] and v.verbose:
				log(v,"Nothing to do (has %s, need %s)" % (v.level,v.start_level))
			return
		level = v.level
		if level > v.max_level:
			level = v.max_level
		want = v.raw_watering_time(level)
		has = timedelta(0,0)
		last_end = None
		for s in v.schedules.filter(start__gte=soon-timedelta(1,0)).order_by('start'):
			last_end=s.end
			if s.end < n:
				continue
#			# This code is disabled because as more 
#			if s.start > later and not s.seen and not s.forced:
#				if options['save']:
#					if v.verbose:
#						log(v,"Drop schedule at %s for %s" % (str_tz(s.start),str(s.duration)))
#					v.update(priority=True)
#					s.delete()
#					continue
			has += s.duration
		if last_end and v.min_delay:
			last_end += v.min_delay

		if has:
			if options['save']:
				v.update(priority=(want.total_seconds() > has.total_seconds()*1.2))
			if v.verbose:
				log(v,"Already something to do (has %s, need %s, want %s, does %s)" % (v.level,v.start_level,want,has))
			return
		elif want.total_seconds() < 10:
			if options['save']:
				v.update(priority=False)
			if v.verbose:
				log(v,"Too little to do (has %s, need %s, want %s)" % (v.level,v.start_level,want))
			return
		if options['verbose']:
			print("Plan",v,"for",want,"Level",v.level,v.start_level,v.stop_level,"P" if v.priority else "")
		for a,b in v.range(start=soon,days=options['age'], add=30):
			if a > soon:
				if options['verbose']:
					print("NotYet",a,soon)
				break # do it during the next run
			if last_end and last_end > a:
				if last_end >= a+b:
					continue
				if last_end>a:
					b-=(last_end-a)
					a=last_end
				last_end=None
			if b.total_seconds() < want.total_seconds()/5:
				if v.verbose:
					log(v,"slot too short at %s for %s (level %s; want %s)" % (str_tz(a),str(b),v.level,str(want)))
				continue
			if v.max_run and b > v.max_run:
				b=v.max_run
			if b < want:
				log(v, "Partial %s %s %s" % (str_tz(a),str(b),str(want)))
				if options['save']:
					sc=Schedule(valve=v,start=a,duration=b)
					sc.save()
					v.update(priority=True)
					if v.verbose:
						log(v,"Scheduled at %s for %s (level %s; want %s)" % (str_tz(a),str(b),v.level,str(want)))
				want -= b
				break # bail out: get others scheduled first / do more in the same slot if v.max_run is set
			else:
				log(v,"Total %s %s" % (str_tz(a),str(want)))
				if options['save']:
					sc=Schedule(valve=v,start=a,duration=want)
					sc.save()
					v.update(priority=False)
					if v.verbose:
						log(v,"Scheduled at %s for %s (level %s)" % (str_tz(a),str(want),v.level))
				want = None
				break
		else:
			if want:
				log(v, "Missing %s" % (str(want),))

	def force_one_valve(self,v,options):
		for a,b in v.range(start=soon,forced=True):
			print("Forced",str_tz(a),str(b))
			if options['save']:
				sc=Schedule(valve=v,start=a,duration=b,forced=True)
				sc.save()


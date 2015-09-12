# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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
		List the current schedule.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller
from rainman.utils import str_tz
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc,get_current_timezone
from optparse import make_option

class Command(BaseCommand):
	args = '<valve>…'
	help = 'Report the schedule for the given valves, or all of them'

	option_list = BaseCommand.option_list + (
			make_option('-s','--site',
				action='store',
				dest='site',
				default=None,
				help='Select the site to report a schedule for'),
			make_option('-c','--controller',
				action='store',
				dest='controller',
				default=None,
				help='Select the controller to report a schedule for (may require --site)'),
			make_option('-i','--interval',
				action='store',
				type=float,
				dest='interval',
				default=None,
				help='report the next N days'),
			make_option('-n','--current',
				action='store_true',
				dest='current',
				default=False,
				help='Also report currently-running activities'),
			make_option('-a','--age',
				action='store',
				type=float,
				dest='age',
				default=None,
				help='History: report N days back, up to the present'),
			)

	def handle(self, *args, **options):
		q = Q()
		now = datetime.utcnow().replace(tzinfo=utc)
		if options['site']:
			q &= Q(controller__site__name=options['site'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		if options['age']:
			if options['interval']:
				raise CommandError("The '--interval' and '--age' options are mutually excusive")
			q &= Q(start__gte=now-timedelta(float(options['age'])))
			q &= Q(start__lt=now)
		else:
			if options['interval']:
				iv = float(options['interval'])
			else:
				iv = 1
			if options['current']:
				q &= Q(start__gt=now-timedelta(1)) # this uses the index
				#q &= Q(start__gt=now-F("db_duration"))
			else:
				q &= Q(start__gte=now)
			q &= Q(start__lt=now+timedelta(iv))

		if len(args):
			for a in args:
				qq = Q(valve__name=a)
				self.one_site(q & qq, options,now)
		else:
			self.one_site(q,options,now)

	def one_site(self,q,options,now):
		"""Print results as a nice minimal table"""
		r = []
		if 'site' not in options:
			r.append("Site")
		if 'controller' not in options:
			r.append("Controller")
		r.extend(("Valve","Start","Dauer","Ende","?"))
		res = [r]
		lengths = [0] * len(r)
		for sched in Schedule.objects.filter(q):
			if options['current'] and sched.start+sched.duration < now:
				continue
			r = []
			if 'site' not in options:
				r.append(sched.controller.site.name)
			if 'controller' not in options:
				r.append(sched.controller.name)
			r.extend((sched.valve.name, str_tz(sched.start), str(sched.duration), str_tz(sched.end), "*" if sched.seen else "-"))
			res.append(r)
		for a in res:
			i=0
			for b in a:
				lb = len(b)
				if lengths[i] < lb:
					lengths[i] = lb
				i += 1
		for a in res:
			r = []
			i=0
			for b in a:
				r.append(b + " "*(lengths[i]-len(b)))
				i += 1
			print(" ".join(r))
			


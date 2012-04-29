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
		List the current schedule.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule
from datetime import datetime,time,timedelta
from django.db.models import F
from django.utils.timezone import utc

class Command(BaseCommand):
	args = '<site> <interval> <valve>…'
	help = 'Report the schedule for the given valves, or all of them'

	def handle(self, *args, **options):
		if len(args):
			try:
				site = Site(name=args[0])
			except Site.DoesNotExist:
				raise CommandError('Site "%s" does not exist' % args[0])
			args = args[1:]
			self.one_site(False,site,args)
		else:
			for site in Site.objects.all():
				self.one_site(True,site,())

	def one_site(self,name_site,site,args):
		interval = 1
		printed = False
		#now=datetime.utcnow()
		now = datetime.utcnow().replace(tzinfo=utc)
		for x in args:
			try:
				interval = float(x)
				continue
			except ValueError:
				try:
					valve = Valve(controller__site=site,name=x)
				except Valve.DoesNotExist:
					raise CommandError('Site "%s" does not have a valve "%s"' % (site.name,x))
			start=now-timedelta(1)
			printed = True
			for sched in Schedule.objects.filter(valve=valve,start__gt=now-F('duration'),start__lt=now+timedelta(interval)):
				if name_site:
					print site.name,
				print sched.start,sched.duration
		if not printed:
			for sched in Schedule.objects.filter(valve__controller__site=site,start__gt=now-F('duration'),start__lt=now+timedelta(interval)):
				if name_site:
					print site.name,
				print sched.valve.name,sched.start,sched.duration

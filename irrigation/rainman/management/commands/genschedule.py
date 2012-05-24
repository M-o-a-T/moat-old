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
		Recalculate valves.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller,History,Level
from rainman.utils import now,str_tz
from rainman.logging import log
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc,get_current_timezone
from optparse import make_option

soon=now()+timedelta(0,15*60)

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
			make_option('-V','--verbose',
				action='store_true',
				dest='verbose',
				default=False,
				help="be more chatty"),
			)

	def handle(self, *args, **options):
		q = Q()
		if options['site']:
			q &= Q(controller__site__name=options['site'])
		if options['group']:
			q &= Q(groups__name=options['group'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		if options['feed']:
			q &= Q(feed__name=options['feed'])
		if len(args):
			for a in args:
				v = Valve.objects.get(q & Q(name=a))
				self.force_one_valve(v, options)
				self.one_valve(v, options)
		else:
			for v in Valve.objects.filter(q).order_by("level"):
				self.force_one_valve(v,options)
			for v in Valve.objects.filter(q).order_by("level"):
				self.one_valve(v,options)

	def one_valve(self,v,options):
		if v.level < v.start_level:
			print "Nothing to do",v,v.level,v.start_level
			if options['save'] and v.verbose:
				log(v,"Nothing to do (has %s, need %s)" % (v.level,v.start_level))
			return
		level = v.level
		if level > v.max_level:
			level = v.max_level
		want = timedelta(0,(level-v.stop_level)*v.area/v.flow)
		for s in v.schedules.filter(start__gte=soon-timedelta(1,0)):
			if s.end < soon:
				continue
			if s.start > soon and not s.seen and not s.forced:
				if options['save']:
					if v.verbose:
						log(v,"Drop schedule at %s for %s" % (str_tz(s.start),str(s.duration)))
					s.delete()
					continue
			#want -= s.duration*1.2 # avoid some strange burst
			want -= timedelta(0,s.duration.total_seconds()*1.2) # timedelta cannot be multiplied (Py3 feature)

		if want.total_seconds() < 10:
			return
		if options['verbose']:
			print "Plan",v,"for",want,"Level",v.level,v.start_level,v.stop_level
		for a,b in v.range(start=soon):
			if b < want:
				print "Partial",str_tz(a),str(b)
				if options['save']:
					sc=Schedule(valve=v,start=a,duration=b)
					sc.save()
					if v.verbose:
						log(v,"Scheduled at %s for %s (level %s; want %s)" % (str_tz(a),str(b),v.level),str(want))
				want -= b
			else:
				print "Total",str_tz(a),str(want)
				if options['save']:
					sc=Schedule(valve=v,start=a,duration=want)
					sc.save()
					if v.verbose:
						log(v,"Scheduled at %s for %s (level %s)" % (str_tz(a),str(want),v.level))
				want = None
				break
		if want is not None:
			print "Missing",want


	def force_one_valve(self,v,options):
		for a,b in v.range(start=soon,forced=True):
			print "Forced",str_tz(a),str(b)
			if options['save']:
				sc=Schedule(valve=v,start=a,duration=b,forced=True)
				sc.save()



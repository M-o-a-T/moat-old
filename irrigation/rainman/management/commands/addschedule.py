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
		Add a schedule entry.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc
from optparse import make_option


class Command(BaseCommand):
	args = '<interval> <valve>'
	help = 'Create a schedule entry for a valve.'

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
				help='Select the controller to use (may require --site)'),
			make_option('-f','--future',
				action='store',
				type=int,
				dest='future',
				default=300,
				help='Create the entry this many seconds in the future'),
			)

	def handle(self, *args, **options):
		q = Q()
		now = datetime.utcnow().replace(tzinfo=utc)
		if options['site']:
			q &= Q(controller__site__name=options['site'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		duration = int(args[0])
		valve = " ".join(args[1:])
		valve = Valve.objects.get(q, var=valve)
		s=Schedule(valve=valve,start=now+timedelta(0,options["future"]),db_duration=duration)
		s.save()


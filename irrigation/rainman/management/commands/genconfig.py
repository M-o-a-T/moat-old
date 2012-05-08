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
		Generate a config file.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc
from optparse import make_option


class Command(BaseCommand):
	args = '<site> <interval> <valve>…'
	help = 'Report the schedule for the given valves, or all of them'

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
			make_option('-t','--type',
				action='store',
				dest='type',
				default="wago",
				help='Controller type'),
			)

	def handle(self, *args, **options):
		q = Q()
		if options['site']:
			q &= Q(controller__site__name=options['site'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		for v in Valve.objects.filter(q):
			self.one_valve(v,options["type"])

	def one_valve(self,v,typ):
		if typ != "wago":
			raise NotImplementedError("I only know type 'wago'")
		print """\
if exists output {name}:
	del output {name}
output wago {cloc} {vloc}:
	name {name}
	bool on off
""".format(name=v.var, vloc=v.location, cloc=v.controller.location)



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

	def add_arguments(self, parser):
		parser.add_argument('-s','--site',
				action='store',
				dest='site',
				default=None,
				help='Limit to this Site (all controllers)')
		parser.add_argument('-c','--controller',
				action='store',
				dest='controller',
				default=None,
				help='Controller to generate a config file snippet for')
		parser.add_argument('-t','--type',
				action='store',
				dest='type',
				default="wago",
				help='Controller type')

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
		print("""\
if exists output {name}:
	del output {name}
if exists on home in command {name}:
	del on home in command {name}
if exists on want output {name}:
	del on want output {name}
if exists on output change {name}:
	del on output change {name}
output wago {cloc} {vloc}:
	name {name}
	bool on off
set output off {name}
trigger home out state {name} :param raw OFF
on home in command {name}:
	name home in command {name}
	var output now {name}
	if equal $raw ON:
		if equal $now off:
			set output on {name} :for 5 min
		else:
			trigger home out state {name} :param raw ON
	else:
		if equal $now on:
			set output off {name}
		else:
			trigger home out state {name} :param raw OFF
on want output {name}:
	name want output {name}
	var output now {name}
	if equal $value on:
		if equal $now off:
			set output on {name} :for 5 min
		else:
			trigger home out state {name} :param raw ON
	else:
		if equal $now on:
			set output off {name}
		else:
			trigger home out state {name} :param raw OFF
on output change {name}:
	name output change {name}
	if equal $value on:
		trigger home out state {name} :param raw ON
	else:
		trigger home out state {name} :param raw OFF

""".format(name=v.var, vloc=v.location, cloc=v.controller.location))


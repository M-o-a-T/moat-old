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
		Generate a config file.
		"""

from django.core.management.base import BaseCommand, CommandError
from rainman.models import Site,Valve,Schedule,Controller,Feed
from datetime import datetime,time,timedelta
from django.db.models import F,Q
from django.utils.timezone import utc
from optparse import make_option

class Command(BaseCommand):
	args = '<site>'
	help = 'Generatr configuration values for openHAB'

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
		qf = Q()
		if options['site']:
			q &= Q(controller__site__name=options['site'])
			qf &= Q(site__name=options['site'])
		if options['controller']:
			q &= Q(controller__name=options['controller'])
		print("""\
Group Water "Gartenwasser" (Out)
""")
		for f in Feed.objects.filter(qf):
			self.one_feed(f)
		for v in Valve.objects.filter(q):
			self.one_valve(v,options["type"])

	def one_feed(self,s):
		print("""\
Group Water_{sname} "{sname}" (Water)
""".format(sname=s.name))
		
	def one_valve(self,v,typ):
		if typ != "wago":
			raise NotImplementedError("I only know type 'wago'")
		sname = "_".join(x[0].upper()+x[1:].lower() for x in v.var.split())
		cname = " ".join(x[0].upper()+x[1:].lower() for x in v.var.split())
		print("""\
Switch {sname} "{cname}" (Water_{site})
""".format(name=v.var, vloc=v.location, cloc=v.controller.location,sname=sname,site=v.feed.name,cname=v.name))


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

import six

from rainman.models import Model
from django.db import models as m
from datetime import timedelta

@six.python_2_unicode_compatible
class Site(Model):
	"""One place with stuff to irrigate."""
	class Meta(Model.Meta):
		db_table="rainman_site"
	def __str__(self):
		return self.name
	name = m.CharField(max_length=200, unique=True)
	comment = m.CharField(max_length=200, blank=True)
	var = m.CharField(max_length=200, unique=True, help_text="name in MoaT", blank=True)
	host = m.CharField(max_length=200, default="localhost", help_text="where to find the RabbitMQ server")
	port = m.PositiveIntegerField(default=0, help_text="Port for RabbitMQ")
	username = m.CharField(max_length=100, default="test", help_text="RabbitMQ username")
	password = m.CharField(max_length=100, default="test", help_text="RabbitMQ password")
	virtualhost = m.CharField(max_length=100, default="/test", help_text="RabbitMQ vhost")

	db_rate = m.FloatField(db_column="rate",default=10/24/3600, help_text="how many mm/day evaporate here, on average")
	def _get_rate(self):
		return self.db_rate*24*3600
	def _set_rate(self,r):
		self.db_rate = r/24/3600
	rate = property(_get_rate,_set_rate)
	db_rain_delay = m.PositiveIntegerField(db_column="rain_delay",default=300,help_text="Wait time after the last sensor says 'no more rain'")
	def _get_rain_delay(self):
		return timedelta(0,self.db_rain_delay)
	def _set_rain_delay(self,val):
		self.db_rain_delay = val.total_seconds()
	rain_delay = property(_get_rain_delay,_set_rain_delay)

	@property
	def valves(self):
		from rainman.models.valve import Valve
		return Valve.objects.filter(controller__site=self)
	@property
	def rate_sec(self):
		return self.rate/24/60/60
	
	@property
	def schedules(self):
		from rainman.models.schedule import Schedule
		return Schedule.objects.filter(valve__controller__site=self)

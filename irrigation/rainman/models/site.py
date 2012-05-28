# -*- coding: utf-8 -*-

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

from __future__ import division,absolute_import
from rainman.models import Model
from django.db import models as m
from datetime import timedelta

class Site(Model):
	"""One place with stuff to irrigate."""
	class Meta(Model.Meta):
		db_table="rainman_site"
	def __unicode__(self):
		return self.name
	name = m.CharField(max_length=200, unique=True)
	var = m.CharField(max_length=200, unique=True, help_text="name in HomEvenT", blank=True)
	host = m.CharField(max_length=200, default="localhost", help_text="where to find the HomEvenT server")
	port = m.PositiveIntegerField(default=50005, help_text="Port for RPC")
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
	def rate_sec(self):
		return self.rate/24/60/60

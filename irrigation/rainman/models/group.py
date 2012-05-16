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
from rainman.models.site import Site
from rainman.models.valve import Valve
from rainman.models.day import Day
from django.db import models as m

class Group(Model):
	class Meta:
		unique_together = (("site", "name"),)
		db_table="rainman_group"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valves = m.ManyToManyField(Valve,related_name="groups")
	site = m.ForeignKey(Site,related_name="groups") # self.valve[*].controller.site is self.site
	#
	# Adjustment factors affecting this group
	adj_rain = m.FloatField(default=1, help_text="How much does rain affect this group?")
	adj_sun = m.FloatField(default=1, help_text="How much does sunshine affect this group?")
	adj_wind = m.FloatField(default=1, help_text="How much does wind affect this group?")
	adj_temp = m.FloatField(default=1, help_text="How much does temperature affect this group?")
	# 
	# when may this group run?
	days = m.ManyToManyField(Day)
	def list_days(self):
		return u"¦".join((d.name for d in self.days.all()))
	def list_valves(self):
		return u"¦".join((d.name for d in self.valves.all()))


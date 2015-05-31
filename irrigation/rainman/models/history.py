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
from rainman.models.controller import Controller
from rainman.utils import now,str_tz
from django.db import models as m

class Level(Model):
	"""historic water levels"""
	class Meta(Model.Meta):
		unique_together = (("valve", "time"),)
		db_table="rainman_level"
	def __str__(self):
		return u"@%s %s" % (str_tz(self.time),self.valve)
	__unicode__=__str__
	valve = m.ForeignKey(Valve, related_name="levels")
	time = m.DateTimeField(db_index=True)
	level = m.FloatField(help_text="then-current water capacity, in mm")
	flow = m.FloatField(default=0, help_text="liters of inflow since the last entry")
	forced = m.BooleanField(default=False,help_text="manually corrected, leave alone when recalculating")

class History(Model):
	"""historic evaporation and rain levels"""
	class Meta(Model.Meta):
		unique_together = (("site", "time"),)
		db_table="rainman_history"
	def __str__(self):
		return u"@%s %s" % (str_tz(self.time),self.site)
	__unicode__=__str__
	site = m.ForeignKey(Site,related_name="history")
	time = m.DateTimeField(db_index=True)
	
	# accumulated volume since the last entry
	rain = m.FloatField(default=0, help_text="how much rain was there (mm)") # measured value
	feed = m.FloatField(default=0, help_text="how much water was used (measured)") # measured value

	# averages since the last entry
	temp = m.FloatField(blank=True,null=True, help_text="average temperature (°C)")
	wind = m.FloatField(blank=True,null=True, help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(blank=True,null=True, help_text="how much sunshine was there (0-1)") # measured value

class Log(Model):
	"""Scheduler and other events"""
	class Meta(Model.Meta):
		#unique_together = (("site","timestamp"),)
		db_table="rainman_log"
		pass
	def __str__(self):
		return u"%s %s" % (self.logger, self.valve or self.controller or self.site)
	__unicode__=__str__
	logger = m.CharField(max_length=200)
	timestamp = m.DateTimeField(default=now,db_index=True)
	site = m.ForeignKey(Site,related_name="logs")
	controller = m.ForeignKey(Controller,related_name="logs", null=True,blank=True)
	valve = m.ForeignKey(Valve,related_name="logs", null=True,blank=True)
	text = m.TextField()


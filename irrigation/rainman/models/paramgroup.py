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
from django.db import models as m

class ParamGroup(Model):
	class Meta:
		unique_together = (("site", "name"),)
		db_table="rainman_paramgroup"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	var = m.CharField(max_length=200,unique=True,help_text="Name in HomEvenT")
	comment = m.CharField(max_length=200,blank=True)
	site = m.ForeignKey(Site,related_name="param_groups")
	factor = m.FloatField(default=1.0, help_text="Base Factor")
	rain = m.BooleanField(default=True,help_text="stop when it's raining?")
	def list_valves(self):
		return u"¦".join((d.name for d in self.valves.all()))

class EnvironmentEffect(Model):
	class Meta:
		db_table="rainman_environmenteffect"
	def __unicode__(self):
		return u"‹%s @%s %s¦%s¦%s›" % (self.__class__.__name__,self.param_group.name,self.temp,self.wind,self.sun)
	param_group = m.ForeignKey(ParamGroup,related_name="environment_effects")
	factor = m.FloatField(default=1.0, help_text="Factor to use at this data point")

	# these are single- or multi-dimensional data points for finding a reasonable factor
	temp = m.FloatField(blank=True,null=True, help_text="average temperature (°C)")
	wind = m.FloatField(blank=True,null=True, help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(blank=True,null=True, help_text="how much sunshine was there (0-1)") # measured value

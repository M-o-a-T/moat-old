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

class Meter(Model):
	class Meta(Model.Meta):
		abstract = True
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.site,self.var)
	name = m.CharField(max_length=200)
	#site = m.ForeignKey(Site,related_name="meters")

class WMeter(Meter):
	class Meta(Meter.Meta):
		abstract = True
	weight = m.PositiveSmallIntegerField(default=10,help_text="how important is this value? 0=presence detector")
	var = m.CharField(max_length=200,unique=True, help_text="monitor name in HomEvenT") # HomEvenT's variable name for it


class RainMeter(WMeter):
	class Meta(WMeter.Meta):
		db_table="rainman_rainmeter"
	pass
	site = m.ForeignKey(Site,related_name="rain_meters")

class TempMeter(WMeter):
	class Meta(WMeter.Meta):
		db_table="rainman_tempmeter"
	pass
	site = m.ForeignKey(Site,related_name="temp_meters")

class WindMeter(WMeter):
	class Meta(WMeter.Meta):
		db_table="rainman_windmeter"
	pass
	site = m.ForeignKey(Site,related_name="wind_meters")

class SunMeter(WMeter):
	class Meta(WMeter.Meta):
		db_table="rainman_sunmeter"
	pass
	site = m.ForeignKey(Site,related_name="sun_meters")


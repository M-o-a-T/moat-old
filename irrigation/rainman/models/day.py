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

class Day(Model):
	"""A generic name for a time description"""
	class Meta:
		db_table="rainman_day"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)

	name = m.CharField(max_length=30, unique=True)
	def list_daytimes(self):
		return u"¦".join((d.descr for d in self.times.all()))

class DayTime(Model):
	"""One element of a time description which is tested"""
	class Meta:
		unique_together = (("day", "descr"),)
		db_table="rainman_daytime"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.descr)

	descr = m.CharField(max_length=200)
	day = m.ForeignKey(Day,related_name="times")


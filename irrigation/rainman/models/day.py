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
from rainman.utils import now, range_union,range_intersection, RangeMixin
from datetime import timedelta
from homevent.times import time_until
from django.utils.timezone import get_current_timezone,make_aware,make_naive

import re

class Day(Model,RangeMixin):
	"""A union of possible elements"""
	class Meta(Model.Meta):
		db_table="rainman_day"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)

	name = m.CharField(max_length=30, unique=True)

	def list_daytimes(self):
		return u"¦".join((d.descr for d in self.times.all()))
	
	def _range(self,start,end):
		return range_union(*(x._range(start,end) for x in self.times.all()))


TimeSplit = re.compile('([-+]?\\d+)?\\s*(\\w+)(?:\s+|$)')

class DayTime(Model,RangeMixin):
	"""One element of a time description which is tested"""
	class Meta(Model.Meta):
		unique_together = (("day", "descr"),)
		db_table="rainman_daytime"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.descr)

	descr = m.CharField(max_length=200)
	day = m.ForeignKey(Day,related_name="times")

	def _range(self,start,end):
		#
		#txt = self.descr.split()
		def j(x):
			for y in x:
				for z in y:
					if z:
						yield z
		txt=list(j(TimeSplit.findall(self.descr)))
		start = make_naive(start,get_current_timezone())
		end = make_naive(end,get_current_timezone())
		while start < end:
			a = time_until(txt, invert=False, now=start)
			b = time_until(txt, invert=True, now=a)
			if b is None:
				import pdb;pdb.set_trace()
				b = time_until(txt, invert=True, now=a)
			yield (make_aware(a,get_current_timezone()), b-a)
			start=b

class DayRange(Model,RangeMixin):
	"""An intersection of possible elements"""
	class Meta(Model.Meta):
		db_table="rainman_dayrange"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)

	name = m.CharField(max_length=30, unique=True)
	days = m.ManyToManyField(Day,related_name="ranges")

	def _range(self,start,end):
		return range_intersection(*list((x._range(start,end) for x in self.days.all())))


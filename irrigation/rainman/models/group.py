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
from rainman.models.day import DayRange
from rainman.utils import now,RangeMixin, range_union,range_intersection,range_invert, str_tz
from django.db import models as m
from datetime import timedelta


class Group(Model,RangeMixin):
	class Meta(Model.Meta):
		unique_together = (("site", "name"),)
		db_table="rainman_group"
	def __unicode__(self):
		return self.name
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="groups") # self.valve[*].controller.site is self.site
	#
	# Adjustment factors affecting this group

#	def get_adj_flow(self,date=None):
#		if date is None:
#			date = now()
#		try:
#			a1 = self.adjusters.filter(start__lte=now).order_by("-start")[0]
#		except IndexError:
#			a1 = None
#		try:
#			a2 = self.adjusters.filter(start__gte=now).order_by("-start")[0]
#		except IndexError:
#			if a1 is None:
#				return 1
#			return a1.factor
#		else:
#			if a1 is None:
#				return a2.factor
#		td = (a2.start-a1.start).total_seconds()
#		if td < 60: # less than one minute? forget it
#			return (a1.factor+a2.factor)/2
#		dd = (date-a1.start).total_seconds()
#		fd = a2.factor - a1.factor
#		return a1.factor + fd * dd / td
#	adj_flow = property(get_adj_flow)

	# 
	# when may this group run? Empty=no restriction
	days = m.ManyToManyField(DayRange,blank=True,related_name="groups_y")
	def list_days(self):
		return u" ¦ ".join((d.name for d in self.days.all()))
	xdays = m.ManyToManyField(DayRange,blank=True,related_name="groups_n")
	def list_xdays(self):
		return u" ¦ ".join((d.name for d in self.xdays.all()))
	
	def list_range(self):
		if self.days.count()+self.xdays.count()+self.overrides.filter(start__gt=now()).count() == 0:
			return u"‹no dates›"
		return super(Group,self).list_range()

	def _range(self,start,end):
		r = []
		r.append(self._days_range(start,end))
		r.append(self._no_xdays_range(start,end))
		r = range_intersection(*r)
		if self.overrides.count():
			r = range_union(r,self._allowed_range(start,end))
		r = range_intersection(r,self._not_blocked_range(start,end))
		return r

	valves = m.ManyToManyField(Valve,related_name="groups")
	def list_valves(self):
		return u" ¦ ".join((d.name for d in self.valves.all()))

	def _not_blocked_range(self,start,end):
		for x in self.overrides.filter(start__gte=start-timedelta(1,0),start__lt=end,allowed=False).order_by("start"):
			if x.end <= start:
				continue
			if x.start > start:
				yield (start,x.start-start)
			start = x.end
		if end>start:
			yield (start,end-start)

	def _allowed_range(self,start,end):
		for x in self.overrides.filter(start__gte=start-timedelta(1,0),start__lt=end,allowed=True).order_by("start"):
			if x.end <= start:
				continue
			if x.start >= start:
				yield (x.start,x.duration)
			else:
				yield (start,x.end-start)
			start = x.end

	def _days_range(self,start,end):
		return range_union(*(d._range(start,end) for d in self.days.all()))

	def _no_xdays_range(self,start,end):
		return range_invert(start,end-start, range_union(*(d._range(start,end) for d in self.xdays.all())))


				



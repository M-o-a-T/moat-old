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
from rainman.models.controller import Controller
from rainman.models.feed import Feed
from rainman.models.env import EnvGroup
from django.db import models as m
from rainman.utils import now, range_intersection,range_union,range_invert, RangeMixin
from datetime import timedelta

class Valve(Model,RangeMixin):
	"""One controller of water"""
	class Meta(Model.Meta):
		unique_together = (("controller", "name"),)
		db_table="rainman_valve"
	def __unicode__(self):
		return self.name
	name = m.CharField(max_length=200)
	comment = m.CharField(max_length=200,blank=True)
	feed = m.ForeignKey(Feed,related_name="valves")
	controller = m.ForeignKey(Controller,related_name="valves")
	envgroup = m.ForeignKey(EnvGroup,db_column="param_group_id",related_name="valves")
	location = m.CharField(max_length=200,help_text="how to identify the valve on its controller")
	var = m.CharField(max_length=200, unique=True, help_text="name of this output, in HomEvenT")
	verbose = m.PositiveSmallIntegerField(default=0,help_text="Log lots of changes?")
	# 
	# This describes the area that's watered
	flow = m.FloatField(help_text="liter/sec when open")
	area = m.FloatField(help_text=u"area in m²")# 1 liter, poured onto 1 m², is 1 mm high
	max_level = m.FloatField(default=10, help_text="stop accumulating dryness") # max water level, in mm: stop counting here
	start_level = m.FloatField(default=8, help_text="start watering above this level") # max water level, in mm: stop counting here
	stop_level = m.FloatField(default=3, help_text="stop watering below this level") # min water level, in mm: start when at/above this
	shade = m.FloatField(default=1, help_text="which part of the standard evaporation rate applies here?")
	runoff = m.FloatField(default=1, help_text="how much incoming rain ends up here?")
	#
#	def get_adj_flow(self,date=None):
#		res = 1
#		for g in self.groups.all():
#			res *= g.get_adj_flow(date)
#		return res
#	adj_flow = property(get_adj_flow)

	def _watering_time(self,level=None):
		if level is None:
			level = self.start_level
		return (level-self.stop_level)*self.area/self.flow
	def raw_watering_time(self,level=None):
		res = self._watering_time(level)
		return timedelta(0,int(res))
	def watering_time(self,level=None,date=None):
		res = self._watering_time(level)
#		res *= self.get_adj_flow(date)
		return timedelta(0,int(res))
	# This describes the current state
	time = m.DateTimeField(db_index=True, default=now, help_text="time when the level was last calculated") # when was the level calculated?
	level = m.FloatField(default=0, help_text="current water capacity, in mm")
	priority = m.BooleanField(help_text="the last cycle did not finish")
	def list_groups(self):
		return u"¦".join((d.name for d in self.groups.all()))

	def _range(self,start,end, forced=False, add=0):
		if start is None:
			start = now()
		r = []


		if forced:
			# If this pass considers force-open times, only this matters
			r.append(self._forced_range(start,end))
		else:
			# Apply groups' times 
			r.append(self._group_range(start,end))
			r.append(self._group_xrange(start,end))

			# First step finished.
			r = [range_intersection(*r)]
			# Now add any group "allowed" one-shots.
			for g in self.groups.all():
				r.append(g._allowed_range(start,end))
			r = [range_union(*r)]

			# Now add any group "not-allowed" one-shots.
			for g in self.groups.all():
				r.append(g._not_blocked_range(start,end))

			# Also apply my own exclusion times
			r.append(self._not_blocked_range(start,end))

		# Exclude times when this valve is already scheduled
		r.append(self._not_scheduled(start,end))

		# Only consider times when the controller can open the valve and
		# there's enough water for it to run
		r.append(self.controller._range(start,end,add=add))
		r.append(self.feed._range(start,end,self.flow,add=add))
		return range_intersection(*r)
	
	def _not_blocked_range(self,start,end):
		for x in self.overrides.filter(start__gte=start-timedelta(1,0),start__lt=end,running=False).order_by("start"):
			if x.end <= start:
				continue
			if x.start > start:
				yield (start,x.start-start)
			start = x.end
		if end>start:
			yield (start,end-start)
				
	def _not_scheduled(self,start,end):
		for x in self.schedules.filter(start__gte=start-timedelta(1,0),start__lt=end).order_by("start"):
			if x.end <= start:
				continue
			if x.start > start:
				yield (start,x.start-start)
			start = x.end+timedelta(0,60)
		if end>start:
			yield (start,end-start)
				
	def _forced_range(self,start,end):
		for x in self.overrides.filter(start__gte=start-timedelta(1,0),start__lt=end,running=True).order_by("start"):
			if x.end <= start:
				continue
			if x.start > start:
				yield (x.start,x.end)
				start = x.end

	def _group_range(self,start,end):
		gx = []
		for g in self.groups.all():
			for gd in g.days.all():
				gx.append(gd._range(start,end))
		return range_union(*gx)

	def _group_xrange(self,start,end):
		gx = []
		for g in self.groups.all():
			for gd in g.xdays.all():
				gx.append(gd._range(start,end))
		return range_invert(start,end-start,range_union(*gx))
				


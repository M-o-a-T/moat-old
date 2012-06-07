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
from rainman.utils import RangeMixin
from rainman.models.meter import Meter
from rainman.models.site import Site
from django.db import models as m
from datetime import timedelta

class Feed(Meter,RangeMixin):
	"""A source of water"""
	class Meta(Model.Meta):
		db_table="rainman_feed"
	site = m.ForeignKey(Site,related_name="feed_meters")
	var = m.CharField(max_length=200,unique=True,blank=True,null=True, help_text="monitor name in HomEvenT") # HomEvenT's variable name for it
	comment = m.CharField(max_length=200,blank=True)

	flow = m.FloatField(default=10, help_text="liters per second")
	db_max_flow_wait = m.PositiveIntegerField(db_column="max_flow_wait",default=300,help_text="Max time for flow measurement")

	def _get_max_flow_wait(self):
		return timedelta(0,self.db_max_flow_wait)
	def _set_max_flow_wait(self,val):
		self.db_max_flow_wait = val.total_seconds()
	max_flow_wait = property(_get_max_flow_wait,_set_max_flow_wait)

	def _range(self,start,end,plusflow,add=0):
		"""Return a range of times which accept this additional flow"""
		if not isinstance(add,timedelta):
			add = timedelta(0,add)
	
		from rainman.models.schedule import Schedule
		from heapq import heappush,heappop

		stops=[]
		flow = self.flow-plusflow
		if flow < 0:
			flow = None # single valve mode

		for s in Schedule.objects.filter(valve__feed=self,start__lt=end,start__gte=start-timedelta(1,0)).order_by("start"):
			if s.start+s.duration <= start:
				continue
			while stops and stops[0][0] < s.start:
				if flow is None:
					nflow = None
					cond=( len(stops)==1 )
				else:
					nflow = flow+stops[0][1]
					cond=( flow<0 and nflow>0 )
				if cond:
					start = stops[0][0]
				flow = nflow
				heappop(stops)

			dflow = s.valve.flow
			heappush(stops,(s.start+s.duration+add,dflow))
			if flow is not None:
				oflow = flow
				flow -= dflow
				cond=( flow<0 and oflow>0 )
			else:
				cond=( len(stops)==1 )
			if cond and start < s.start:
				yield ((start,s.start-start))

		while stops and (flow<0 if flow is not None else True):
			start=stops[0][0]
			if flow is not None:
				flow += stops[0][1]
			heappop(stops)
		if end>start:
			yield ((start,end-start))

	@property
	def schedules(self):
		from rainman.models.schedule import Schedule
		return Schedule.objects.filter(valve__feed=self)


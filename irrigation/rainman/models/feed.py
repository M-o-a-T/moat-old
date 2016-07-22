# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

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
	var = m.CharField(max_length=200,unique=True,blank=True,null=True, help_text="monitor name in MoaT") # MoaT's variable name for it
	comment = m.CharField(max_length=200,blank=True)

	flow = m.FloatField(default=10, blank=True,null=True,help_text="liters per second")
	db_max_flow_wait = m.PositiveIntegerField(db_column="max_flow_wait",default=300,help_text="Max time for flow measurement")
	disabled = m.BooleanField(default=False,max_length=1,help_text="OFF: don't schedule my valves")

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
		if self.flow is None:
			flow = None
		else:
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


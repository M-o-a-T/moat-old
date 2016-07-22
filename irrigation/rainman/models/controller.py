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

import six

from rainman.models import Model
from rainman.models.site import Site
from rainman.utils import RangeMixin,str_tz
from django.db import models as m
from datetime import timedelta

@six.python_2_unicode_compatible
class Controller(Model,RangeMixin):
	"""A thing (Wago or whatever) which controls valves."""
	class Meta(Model.Meta):
		unique_together = (("site", "name"),)
		db_table="rainman_controller"
	def __str__(self):
		return self.name
	name = m.CharField(max_length=200)
	var = m.CharField(max_length=200,unique=True,help_text="Name in MoaT")
	comment = m.CharField(max_length=200,blank=True,help_text="Comment")
	site = m.ForeignKey(Site,related_name="controllers")
	location = m.CharField(max_length=200, help_text="How to identify the controller (host name?)")
	max_on = m.IntegerField(default=3, help_text="number of valves that can be on at any one time")

	def _range(self,start,end, add=0):
		if not isinstance(add,timedelta):
			add = timedelta(0,add)

		from rainman.models.schedule import Schedule
		from heapq import heappush,heappop
		stops=[]
		n_open = 0

		for s in Schedule.objects.filter(valve__controller=self,start__lt=end,start__gte=start-timedelta(1,0)).order_by("start"):
			if s.start+s.duration <= start:
				continue
			while stops and stops[0] < s.start:
				if n_open == self.max_on:
					start = stops[0]
				k=heappop(stops)
				#print("-",n_open,str_tz(k))
				n_open -= 1
			n_open += 1
			heappush(stops,s.start+s.duration+add)
			#print("+",n_open,str_tz(s.start+s.duration))
			if n_open == self.max_on:
				if (start < s.start):
					yield ((start,s.start-start))

		while n_open >= self.max_on and len(stops):
			n_open -= 1
			start=heappop(stops)
		if end>start:
			yield ((start,end-start))

	@property
	def schedules(self):
		from rainman.models.schedule import Schedule
		return Schedule.objects.filter(valve__controller=self)


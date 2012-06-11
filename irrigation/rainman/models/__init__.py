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

from django.db import models as m
from rainman.utils import now

class Model(m.Model):
	class Meta:
		abstract = True
		app_label = 'rainman'

	def __repr__(self):
		return u'‹%s %s›' % (self.__class__.__name__,unicode(self))

	def refresh(self):
		"""Refreshes this instance from db"""
		from_db = self.__class__.objects.get(pk=self.pk)
		fields = self.__class__._meta.get_all_field_names()
		
		for field in fields:
			try:
				val = getattr(from_db, field)
			except AttributeError:
				continue
			# unfortunately these classes are not accessible externally
			# so we have to check by name
			if val.__class__.__name__ not in ("RelatedManager","ManyRelatedManager"):
				setattr(self, field, val)
	def sync(self):
		pass
	def shutdown(self):
		pass
	def update(self,**k):
		self.__class__.objects.filter(id=self.id).update(**k)


from rainman.models.site import Site
from rainman.models.feed import Feed
from rainman.models.controller import Controller
from rainman.models.env import EnvGroup,EnvItem
from rainman.models.valve import Valve
from rainman.models.history import Level,History,Log
from rainman.models.day import Day,DayTime,DayRange
from rainman.models.group import Group
from rainman.models.override import GroupOverride,ValveOverride,GroupAdjust
from rainman.models.schedule import Schedule
from rainman.models.meter import RainMeter,TempMeter,WindMeter,SunMeter
from rainman.models.auth import UserForSite


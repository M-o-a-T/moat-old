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
from django.db import models as m
from rainman.utils import now

class Model(m.Model):
	class Meta:
		abstract = True
		app_label = 'rainman'

	def __repr__(self):
		return u'‹%s %s›' % (self.__class__.__name__,six.text_type(self))

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


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
from rainman.models.meter import Meter
from rainman.models.site import Site
from django.db import models as m
from datetime import timedelta

class Feed(Meter):
	"""A source of water"""
	class Meta:
		db_table="rainman_feed"
	site = m.ForeignKey(Site,related_name="feed_meters")
	db_max_flow_wait = m.PositiveIntegerField(db_column="max_flow_wait",default=300,help_text="Max time for flow measurement")
	def _get_max_flow_wait(self):
		return timedelta(0,self.db_max_flow_wait)
	def _set_max_flow_wait(self,val):
		self._max_flow_wait = timedelta(0,self.db_max_flow_wait)
	max_flow_wait = property(_get_max_flow_wait,_set_max_flow_wait)


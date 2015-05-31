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
from rainman.models.valve import Valve
from django.db import models as m
from datetime import timedelta
from rainman.utils import str_tz

class Schedule(Model):
	"""The actual plan"""
	class Meta(Model.Meta):
		unique_together = (("valve","start"),)
		db_table="rainman_schedule"
	def __str__(self):
		return u"@%s %s" % (str_tz(self.start),self.valve)
	__unicode__=__str__
	valve = m.ForeignKey(Valve,related_name="schedules")
	start = m.DateTimeField(db_index=True)
	db_duration = m.PositiveIntegerField(db_column="duration")
	def _get_duration(self):
		if self.db_duration is not None:
			return timedelta(0,self.db_duration)
	def _set_duration(self,val):
		self.db_duration = val.total_seconds()
	duration = property(_get_duration,_set_duration)
	@property
	def end(self):
		return self.start+self.duration

	seen = m.BooleanField(default=False,max_length=1,help_text="Sent to the controller?")
	changed = m.BooleanField(default=False,max_length=1,help_text="Updated by the scheduler?")
	forced = m.BooleanField(default=False,max_length=1,help_text="Generated due to a valve force entry?")
	# The scheduler inserts both to False. The controller sets Seen.
	# if the scheduler has to change something, it clears Seen and sets Change


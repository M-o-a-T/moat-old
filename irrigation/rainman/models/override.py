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
from rainman.models.group import Group
from rainman.models.valve import Valve
from django.db import models as m
from datetime import timedelta

class GroupOverride(Model):
	"""Modify schedule times"""
	class Meta:
		unique_together = (("group", "name"),("group","start"))
		db_table="rainman_groupoverride"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	group = m.ForeignKey(Group,related_name="overrides")
	allowed = m.BooleanField() # whether to allow these to run(True) or not(False)
	start = m.DateTimeField(db_index=True)
	db_duration = m.PositiveIntegerField(db_column="duration")
	def _get_duration(self):
		return timedelta(0,self.db_duration)
	def _set_duration(self,val):
		self._duration = timedelta(0,self.db_duration)
	duration = property(_get_duration,_set_duration)
	on_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	off_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	
class ValveOverride(Model):
	"""Force schedule times"""
	class Meta:
		unique_together = (("valve", "name"),("valve","start"))
		db_table="rainman_valveoverride"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valve = m.ForeignKey(Valve,related_name="overrides")
	running = m.BooleanField() # whether to force on(True) or off(False)
	start = m.DateTimeField(db_index=True)
	db_duration = m.PositiveIntegerField(db_column="duration")
	def _get_duration(self):
		return timedelta(0,self.db_duration)
	def _set_duration(self,val):
		self._duration = timedelta(0,self.db_duration)
	duration = property(_get_duration,_set_duration)
	on_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	off_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	
class GroupAdjust(Model):
	"""Beginning at this date, this group needs <modifier> more(>1)/less(<1) water.
		To turn the whole thing off, set modifier=0.
		Any entry is valid until superseded by one with later start."""
	class Meta:
		unique_together = (("group","start"),)
		db_table="rainman_groupadjust"
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.group)
	group = m.ForeignKey(Group,related_name="adjusters")
	start = m.DateTimeField(db_index=True)
	factor = m.FloatField()


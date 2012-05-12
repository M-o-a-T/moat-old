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

from datetime import datetime,time,timedelta
from django.db import models as m
from rainman.utils import now

class Site(m.Model):
	"""One place with stuff to irrigate."""
	class Meta:
		pass
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200, unique=True)
	host = m.CharField(max_length=200, default="localhost", help_text="where to find the HomEvenT server")
	port = m.PositiveIntegerField(default=50005, help_text="Port for RPC")
	rate = m.FloatField(default=2, help_text="how many mm/day evaporate here, on average")
	_rain_delay = m.PositiveIntegerField("rain_delay",default=300,help_text="Wait time after the last sensor says 'no more rain'")
	def _get_rain_delay(self):
		return timedelta(0,self._rain_delay)
	def _set_rain_delay(self,val):
		self._rain_delay = timedelta(0,self._rain_delay)
	rain_delay = property(_get_rain_delay,_set_rain_delay)

	@property
	def rate_sec(self):
		return self.rate/24/60/60
	
class Feed(m.Model):
	"""A source of water"""
	class Meta:
		unique_together = (("site", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="feed_meters")
	flow = m.FloatField(default=10, help_text="liters per second")
	var = m.CharField(max_length=200, help_text="flow counter variable", blank=True)

class Controller(m.Model):
	"""A thing (Wago or whatever) which controls valves."""
	class Meta:
		unique_together = (("site", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="controllers")
	location = m.CharField(max_length=200, help_text="How to identify the controller (host name?)")
	max_on = m.IntegerField(default=3, help_text="number of valves that can be on at any one time")

class ParamGroup(m.Model):
	class Meta:
		unique_together = (("site", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	comment = m.CharField(max_length=200,blank=True)
	site = m.ForeignKey(Site,related_name="param_groups")
	factor = m.FloatField(default=1.0, help_text="Base Factor")
	rain = m.BooleanField(default=True,help_text="affected by rain?")
	def list_valves(self):
		return u"¦".join((d.name for d in self.valves.all()))

class Valve(m.Model):
	"""One controller of water"""
	class Meta:
		unique_together = (("controller", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	comment = m.CharField(max_length=200,blank=True)
	feed = m.ForeignKey(Feed,related_name="valves")
	controller = m.ForeignKey(Controller,related_name="valves")
	param_group = m.ForeignKey(ParamGroup,related_name="valves")
	location = m.CharField(max_length=200,help_text="how to identify the valve on its controller")
	var = m.CharField(max_length=200, help_text="name of this output, in HomEvenT")
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
	# This describes the current state
	time = m.DateTimeField(db_index=True, help_text="time when the level was last calculated") # when was the level calculated?
	level = m.FloatField(default=0, help_text="current water capacity, in mm")
	priority = m.BooleanField(help_text="the last cycle did not finish")
	def list_groups(self):
		return u"¦".join((d.name for d in self.groups.all()))

class Level(m.Model):
	"""historic water levels"""
	class Meta:
		unique_together = (("valve", "time"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.valve)
	valve = m.ForeignKey(Valve, related_name="levels")
	time = m.DateTimeField(db_index=True)
	level = m.FloatField(help_text="then-current water capacity, in mm")
	flow = m.FloatField(default=0, help_text="m³ since last entry")

class History(m.Model):
	"""historic evaporation and rain levels"""
	class Meta:
		unique_together = (("site", "time"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.site)
	site = m.ForeignKey(Site,related_name="history")
	time = m.DateTimeField(db_index=True)
	
	# accumulated volume since the last entry
	rain = m.FloatField(default=0, help_text="how much rain was there (mm)") # measured value
	feed = m.FloatField(default=0, help_text="how much water was used (measured)") # measured value

	# averages since the last entry
	temp = m.FloatField(blank=True,null=True, help_text="average temperature (°C)")
	wind = m.FloatField(blank=True,null=True, help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(blank=True,null=True, help_text="how much sunshine was there (0-1)") # measured value

class EnvironmentEffect(m.Model):
	class Meta:
		pass
	def __unicode__(self):
		return u"‹%s @%s %s¦%s¦%s›" % (self.__class__.__name__,self.site.name,self.temp,self.wind,self.sun)
	param_group = m.ForeignKey(Site,related_name="environment_effects")
	factor = m.FloatField(default=1.0, help_text="Factor to use at this data point")

	# these are single- or multi-dimensional data points for finding a reasonable factor
	temp = m.FloatField(blank=True,null=True, help_text="average temperature (°C)")
	wind = m.FloatField(blank=True,null=True, help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(blank=True,null=True, help_text="how much sunshine was there (0-1)") # measured value

class Day(m.Model):
	"""A generic name for a time description"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=30, unique=True)
	def list_daytimes(self):
		return u"¦".join((d.descr for d in self.times.all()))

class DayTime(m.Model):
	"""One element of a time description which is tested"""
	class Meta:
		unique_together = (("day", "descr"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.descr)
	descr = m.CharField(max_length=200)
	day = m.ForeignKey(Day,related_name="times")

class Group(m.Model):
	class Meta:
		unique_together = (("site", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valves = m.ManyToManyField(Valve,related_name="groups")
	site = m.ForeignKey(Site,related_name="groups") # self.valve[*].controller.site is self.site
	#
	# Adjustment factors affecting this group
	adj_rain = m.FloatField(default=1, help_text="How much does rain affect this group?")
	adj_sun = m.FloatField(default=1, help_text="How much does sunshine affect this group?")
	adj_wind = m.FloatField(default=1, help_text="How much does wind affect this group?")
	adj_temp = m.FloatField(default=1, help_text="How much does temperature affect this group?")
	# 
	# when may this group run?
	days = m.ManyToManyField(Day)
	def list_days(self):
		return u"¦".join((d.name for d in self.days.all()))
	def list_valves(self):
		return u"¦".join((d.name for d in self.valves.all()))

class GroupOverride(m.Model):
	"""Modify schedule times"""
	class Meta:
		unique_together = (("group", "name"),("group","start"))
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	group = m.ForeignKey(Group,related_name="overrides")
	allowed = m.BooleanField() # whether to allow these to run(True) or not(False)
	start = m.DateTimeField(db_index=True)
	duration = m.TimeField()
	on_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	off_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	
class ValveOverride(m.Model):
	"""Force schedule times"""
	class Meta:
		unique_together = (("valve", "name"),("valve","start"))
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valve = m.ForeignKey(Valve,related_name="overrides")
	running = m.BooleanField() # whether to force on(True) or off(False)
	start = m.DateTimeField(db_index=True)
	duration = m.TimeField()
	on_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	off_level = m.FloatField(blank=True,null=True,default=None,help_text="Level above(off)/below(on) which to activate this rule (factor of max)")
	
class GroupAdjust(m.Model):
	"""Beginning at this date, this group needs <modifier> more(>1)/less(<1) water.
		To turn the whole thing off, set modifier=0.
		Any entry is valid until superseded by one with later start."""
	class Meta:
		unique_together = (("group","start"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.group)
	group = m.ForeignKey(Group,related_name="adjusters")
	start = m.DateTimeField(db_index=True)
	factor = m.FloatField()

class Schedule(m.Model):
	"""The actual plan"""
	class Meta:
		unique_together = (("valve","start"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.valve)
	valve = m.ForeignKey(Valve,related_name="schedules")
	start = m.DateTimeField(db_index=True)
	duration = m.TimeField()
	seen = m.BooleanField(default=False,max_length=1,help_text="Sent to the controller?")
	changed = m.BooleanField(default=False,max_length=1,help_text="Updated by the scheduler?")
	# The scheduler inserts both to False. The controller sets Seen.
	# if the scheduler has to change something, it clears Seen and sets Change

class RainMeter(m.Model):
	"""The rain in Spain stays mainly in the plain."""
	class Meta:
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.site,self.var)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="rain_meters")
	var = m.CharField(max_length=200,help_text="monitor name in HomEvenT") # HomEvenT's variable name for it
	weight = m.PositiveSmallIntegerField(default=10,help_text="how important is this value? 0=presence detector")

class TempMeter(m.Model):
	"""The rain in Spain stays mainly in the plain."""
	class Meta:
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.site,self.var)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="temp_meters")
	var = m.CharField(max_length=200,help_text="monitor name in HomEvenT") # HomEvenT's variable name for it
	weight = m.PositiveSmallIntegerField(default=10,help_text="how important is this value?")

class WindMeter(m.Model):
	"""obvious what this is for ;-)"""
	class Meta:
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.site,self.var)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="wind_meters")
	var = m.CharField(max_length=200,help_text="monitor name in HomEvenT") # HomEvenT's variable name for it
	weight = m.PositiveSmallIntegerField(default=10,help_text="how important is this value?")

class SunMeter(m.Model):
	"""I am the sunshine of your … garden."""
	class Meta:
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.site,self.var)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="sun_meters")
	var = m.CharField(max_length=200,help_text="monitor name in HomEvenT") # HomEvenT's variable name for it
	weight = m.PositiveSmallIntegerField(default=10,help_text="how important is this value?")

class Log(m.Model):
	"""Scheduler and other events"""
	class Meta:
		#unique_together = (("site","timestamp"),)
		pass
	def __unicode__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.logger, self.valve or self.controller or self.site)
	logger = m.CharField(max_length=200)
	timestamp = m.DateTimeField(default=now,db_index=True)
	site = m.ForeignKey(Site,related_name="logs")
	controller = m.ForeignKey(Controller,related_name="logs", null=True,blank=True)
	valve = m.ForeignKey(Valve,related_name="logs", null=True,blank=True)
	text = m.TextField()

from django.contrib.auth.models import User as DjangoUser
class UserForGroup(m.Model):
	"""Limit Django users to a specific group"""
	class Meta:
		pass
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.user.username,self.group.name)
	user = m.ForeignKey(DjangoUser)
	group = m.ForeignKey(Group,related_name="users")
	LEVEL_VALUES = (
		('0',"None"),
		('1',"read"),
		('2',"change schedule"),
		('3',"admin"),
	)
	level = m.IntegerField(choices=LEVEL_VALUES,default=1,help_text=u"Access to …")



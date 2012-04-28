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

from django.db import models as m
from django.utils import timezone


class Site(m.Model):
	"""One site with stuff to irrigate."""
	class Meta:
		pass
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200, unique=True)
	host = m.CharField(max_length=200, default="localhost", help_text="where to find the HomEvenT server")
	rate = m.FloatField(default=2, help_text="how many mm/day evaporate here, on average")

class Feed(m.Model):
	"""A source of water"""
	class Meta:
		unique_together = (("site", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="feeds")
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
	max_on = m.IntegerField(default=3, help_text="number of valves that can be on at any one time")

class Valve(m.Model):
	class Meta:
		unique_together = (("controller", "name"),)
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	comment = m.CharField(max_length=200)
	feed = m.ForeignKey(Feed,related_name="valves")
	controller = m.ForeignKey(Controller,related_name="valves")
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
	time = m.DateTimeField(help_text="time when the level was last calculated") # when was the level calculated?
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
	time = m.DateTimeField()
	level = m.FloatField(help_text="then-current water capacity, in mm")
	flow = m.FloatField(default=0, help_text="actual water flow through the valve")

class History(m.Model):
	"""historic evaporation and rain levels"""
	class Meta:
		unique_together = (("site", "time"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.site)
	site = m.ForeignKey(Site,related_name="history")
	time = m.DateTimeField()
	
	# These values accumulate from this record's "time" until the next
	rate = m.FloatField(help_text="how much water evaporated (mm)") # calculated value
	rain = m.FloatField(help_text="how much rain was there (mm)") # measured value

class Environment(m.Model):
	"""historic environmental data"""
	class Meta:
		unique_together = (("site", "time"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.site)
	site = m.ForeignKey(Site,related_name="environments")
	time = m.DateTimeField()

	temp = m.FloatField(help_text="average temperature (°C)")
	wind = m.FloatField(help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(help_text="how much sunshine was there (0-1)") # measured value

class EnvironmentEffect(m.Model):
	class Meta:
		unique_together = (("site", "temp","wind","sun"),)
	def __unicode__(self):
		return u"‹%s @%s %s¦%s¦%s›" % (self.__class__.__name__,self.site.name,self.temp,self.wind,self.sun)
	site = m.ForeignKey(Site,related_name="environment_effects")
	factor = m.FloatField(help_text="Factor to use at this data point")

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
	start = m.DateTimeField()
	duration = m.TimeField()
	
class ValveOverride(m.Model):
	"""Force schedule times"""
	class Meta:
		unique_together = (("valve", "name"),("valve","start"))
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valve = m.ForeignKey(Valve,related_name="overrides")
	running = m.BooleanField() # whether to force on(True) or off(False)
	start = m.DateTimeField()
	duration = m.TimeField()
	
class GroupAdjust(m.Model):
	"""Beginning at this date, this group needs <modifier> more(>1)/less(<1) water.
		To turn the whole thing off, set modifier=0.
		Any entry is valid until superseded by one with later start."""
	class Meta:
		unique_together = (("group","start"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.group)
	group = m.ForeignKey(Group,related_name="adjusters")
	start = m.DateTimeField()
	factor = m.FloatField()

class Schedule(m.Model):
	"""The actual plan"""
	class Meta:
		unique_together = (("valve","start"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.valve)
	valve = m.ForeignKey(Valve,related_name="schedules")
	start = m.DateTimeField()
	duration = m.TimeField()
	SEEN_VALUES = (
		('y',"set"),
		('n',"not set"),
		('c',"changed"),
	)
	seen = m.BooleanField(default=False,max_length=1,help_text="Sent to the controller?")
	changed = m.BooleanField(default=False,max_length=1,help_text="Updated by the scheduler?")
	# The scheduler inserts both to False. The controller sets Seen.
	# if the scheduler has to change something, it clears Seen and sets Change

class RainMeter(m.Model):
	"""The rain in Spain stays mainly in the plain."""
	class Meta:
		unique_together = (("site","name"),)
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.controller,self.var)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="rain_meters")
	controller = m.ForeignKey(Controller,related_name="rain_meters")
	var = m.CharField(max_length=200) # HomEvenT's variable name for it


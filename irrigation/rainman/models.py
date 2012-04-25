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
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	rate = m.FloatField(default=2) # how many mm/day evaporate here, currently

class Feed(m.Model):
	"""A source of water"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="feeds")
	flow = m.FloatField(default=10) # l/sec

class Controller(m.Model):
	"""A thing (Wago or whatever) which controls valves."""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	site = m.ForeignKey(Site,related_name="controllers")
	max_on = m.IntegerField(default=3) # number of valves that can be on at any one time
	host = m.CharField(max_length=200) # where to find the controller

class Valve(m.Model):
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	feed = m.ForeignKey(Feed,related_name="valves")
	controller = m.ForeignKey(Controller,related_name="valves")
	var = m.CharField(max_length=200) # HomEvenT's variable name for it
	# 
	# This describes the area that's watered
	flow = m.FloatField() # liter/sec when open
	area = m.FloatField() # wetted area in m²: 1 liter, poured onto 1 m², is 1 mm high
	max_level = m.FloatField(default=10) # max water level, in mm: stop here
	min_level = m.FloatField(default=3) # min water level, in mm: start when at/below this
	shade = m.FloatField(default=1) # how much of the standard evaporation rate applies here?
	#
	# This describes the current state
	time = m.DateTimeField(default=timezone.now) # when was the level calculated?
	level = m.FloatField(default=0) # current water level, in mm

class Level(m.Model):
	"""historic water levels"""
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.valve)
	valve = m.ForeignKey(Valve, related_name="levels")
	time = m.DateTimeField()
	level = m.FloatField() # then-current water level, in mm
	is_open = m.BooleanField(default=False) # was the valve open when this started?

class Evaporation(m.Model):
	"""historic evaporation levels"""
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.time,self.site)
	site = m.ForeignKey(Site,related_name="evaporations")
	time = m.DateTimeField()
	rate = m.FloatField() # how many mm/day evaporate

class Day(m.Model):
	"""A generic name for a time description"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=30)

class DayTime(m.Model):
	"""One element of a time description which is tested"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.descr)
	descr = m.CharField(max_length=200)
	day = m.ForeignKey(Day,related_name="times")

class Group(m.Model):
	name = m.CharField(max_length=200)
	valves = m.ManyToManyField(Valve)
	site = m.ForeignKey(Site,related_name="groups") # self.valve[*].controller.site is self.site
	#
	# when may this group run?
	days = m.ManyToManyField(Day)

class GroupOverride(m.Model):
	"""Modify schedule times"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	group = m.ForeignKey(Group,related_name="overrides")
	allowed = m.BooleanField() # whether to allow these to run(True) or not(False)
	start = m.DateTimeField()
	duration = m.IntegerField()
	
class ValveOverride(m.Model):
	"""Force schedule times"""
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	valve = m.ForeignKey(Valve,related_name="overrides")
	running = m.BooleanField() # whether to force on(True) or off(False)
	start = m.DateTimeField()
	duration = m.IntegerField()
	
class GroupAdjust(m.Model):
	"""Beginning at this date, this group needs <modifier> more(>1)/less(<1) water.
		To turn the whole thing off, set modifier=0.
		Any entry is valid until superseded by one with later start."""
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.group)
	group = m.ForeignKey(Group,related_name="adjusters")
	start = m.DateTimeField()
	factor = m.FloatField()

class Schedule(m.Model):
	"""The actual plan"""
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.start,self.valve)
	valve = m.ForeignKey(Valve,related_name="schedules")
	start = m.DateTimeField()
	duration = m.IntegerField()



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
from rainman.models.site import Site
from django.db import models as m
from django.db.models import Q

class ParamGroup(Model):
	class Meta:
		unique_together = (("site", "name"),)
		db_table="rainman_paramgroup"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	var = m.CharField(max_length=200,unique=True,help_text="Name in HomEvenT")
	comment = m.CharField(max_length=200,blank=True)
	site = m.ForeignKey(Site,related_name="param_groups")
	factor = m.FloatField(default=1.0, help_text="Base Factor")
	rain = m.BooleanField(default=True,help_text="stop when it's raining?")

	def __init__(self,*a,**k):
		super(ParamGroup,self).__init__(*a,**k)
		self.env_cache = {}

	def list_valves(self):
		return u"¦".join((d.name for d in self.valves.all()))

	def refresh(self):
		super(ParamGroup,self).refresh()
		self.env_cache = {}

	def env_factor_one(self, tws, h):
		p=4 # power factor, favoring nearest-neighbor

		qtemp,qwind,qsun = tws
		if qtemp and h.temp is None: return None
		if qwind and h.wind is None: return None
		if qsun and h.sun is None: return None
		q=Q()
		q &= Q(temp__isnull=not qtemp)
		q &= Q(wind__isnull=not qwind)
		q &= Q(sun__isnull=not qsun)

		sum_f = 0
		sum_w = 0
		try:
			ec = self.env_cache[tws]
		except KeyError:
			self.env_cache[tws] = ec = list(self.environment_effects.filter(q))
		for ef in ec:
			d=0
			if qtemp:
				d += (h.temp-ef.temp)**2
			if qwind:
				d += (h.wind-ef.wind)**2
			if qsun:
				d += (h.sun-ef.sun)**2
			d = d**(p*0.5)
			if d < 0.001: # close enough
				return ef.factor
			sum_f += ef.factor/d
			sum_w += 1/d
		if not sum_w:
			return None
		return sum_f / sum_w


	def env_factor(self, h, logger=None):
		"""Calculate a weighted factor for history entry @h, based on the given environmental parameters"""
		ql=(
			(6,(True,True,True)),
			(4,(False,True,True)),
			(4,(True,False,True)),
			(4,(True,True,False)),
			(1,(True,False,False)),
			(1,(False,True,False)),
			(1,(False,False,True)),
			)
		sum_f = 0.01 # if there are no data, return 1
		sum_w = 0.01
		for weight,tws in ql:
			f = self.env_factor_one(tws,h)
			if f is not None:
				if logger:
					logger("Simple factor %s%s%s: %f" % ("T" if tws[0] else "-", "W" if tws[1] else "-", "S" if tws[2] else "-", f))
				sum_f += f*weight
				sum_w += weight
		return sum_f / sum_w

class EnvironmentEffect(Model):
	class Meta:
		db_table="rainman_environmenteffect"
	def __unicode__(self):
		return u"‹%s @%s %s¦%s¦%s›" % (self.__class__.__name__,self.param_group.name,self.temp,self.wind,self.sun)
	param_group = m.ForeignKey(ParamGroup,related_name="environment_effects")
	factor = m.FloatField(default=1.0, help_text="Factor to use at this data point")

	# these are single- or multi-dimensional data points for finding a reasonable factor
	temp = m.FloatField(blank=True,null=True, help_text="average temperature (°C)")
	wind = m.FloatField(blank=True,null=True, help_text="wind speed (m/s or whatever)")
	sun = m.FloatField(blank=True,null=True, help_text="how much sunshine was there (0-1)") # measured value

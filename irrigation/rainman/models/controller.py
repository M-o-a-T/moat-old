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

class Controller(Model):
	"""A thing (Wago or whatever) which controls valves."""
	class Meta:
		unique_together = (("site", "name"),)
		db_table="rainman_controller"
	def __unicode__(self):
		return u"‹%s %s›" % (self.__class__.__name__,self.name)
	name = m.CharField(max_length=200)
	var = m.CharField(max_length=200,unique=True,help_text="Name in HomEvenT")
	site = m.ForeignKey(Site,related_name="controllers")
	location = m.CharField(max_length=200, help_text="How to identify the controller (host name?)")
	max_on = m.IntegerField(default=3, help_text="number of valves that can be on at any one time")


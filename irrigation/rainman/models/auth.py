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
from rainman.models.valve import Valve
from rainman.models.feed import Feed
from rainman.models.controller import Controller
from rainman.models.group import Group
from rainman.models.env import EnvGroup
from django.db import models as m
from django.db.models.signals import post_save

from django.contrib.auth.models import User as DjangoUser

LEVEL_VALUES = (
	(0,"None"),
	(1,"read"),
	(2,"change schedule"),
	(3,"admin"),
)

class UserForSite(Model):
	"""Limit Django users to some sites"""
	class Meta(Model.Meta):
		db_table="rainman_userforsite"
	def __unicode__(self):
		return u"@%s %s" % (self.user.username,u"¦".join(s.name for s in self.sites.all()))
	user = m.OneToOneField(DjangoUser)
	sites = m.ManyToManyField(Site, blank=True, related_name="users",help_text="Sites this user may access")
	valves = m.ManyToManyField(Valve, blank=True, related_name="users",help_text="Valves this user may access")
	level = m.PositiveSmallIntegerField(choices=LEVEL_VALUES,default=1,help_text=u"Access to …")

	@property
	def feeds(self):
		if self.level >= 3:
			return Feed.objects.filter(site__in=self.sites.all()).distinct()
		return Feed.objects.filter(valves__in=self.valves.all()).distinct()

	@property
	def envgroups(self):
		if self.level >= 3:
			return EnvGroup.objects.filter(site__in=self.sites.all()).distinct()
		return EnvGroup.objects.filter(valves__in=self.valves.all()).distinct()

	@property
	def controllers(self):
		if self.level >= 3:
			return Controller.objects.filter(site__in=self.sites.all()).distinct()
		return Controller.objects.filter(valves__in=self.valves.all()).distinct()

	@property
	def groups(self):
		if self.level >= 3:
			return Group.objects.filter(site__in=self.sites.all()).distinct()
		return Group.objects.filter(valves__in=self.valves.all()).distinct()

	@property
	def all_valves(self):
		if self.level >= 3:
			return Valve.objects.filter(controller__site__in=self.sites.all())
		return self.valves.all()

	def access_site(self,site):
		if self.sites.filter(id==site.id).count():
			return self.level
		return False

	def access_valve(self,valve):
		if not self.sites.filter(id=valve.feed.site.id).distinct().count():
			return False
		if self.level >= 3:
			return self.level
		if self.valves.filter(id=valve.id).distinct().count():
			return self.level
		return False

	def access_feed(self,feed):
		if not self.sites.filter(id=feed.site.id).unique().count():
			return False
		if self.level >= 3:
			return self.level
		if self.valves.filter(feed__id=feed.id).unique().count():
			return self.level
		return False

	def access_controller(self,controller):
		if not self.sites.filter(id=controller.site.id).unique().count():
			return False
		if self.level >= 3:
			return self.level
		if self.valves.filter(controller__id=controller.id).unique().count():
			return self.level
		return False

	def access_group(self,group):
		if not self.sites.filter(id=group.site.id).unique().count():
			return False
		if self.level >= 3:
			return self.level
		if self.valves.filter(group__id=group.id).unique().count():
			return self.level
		return False



# definition of UserProfile from above
# ...

def create_user_profile(sender, instance, created, **kwargs):
	if created:
		UserForSite.objects.create(user=instance)

post_save.connect(create_user_profile, sender=DjangoUser)

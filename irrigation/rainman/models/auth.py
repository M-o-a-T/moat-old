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
from django.db import models as m
from django.db.models.signals import post_save

from django.contrib.auth.models import User as DjangoUser
class UserForGroup(Model):
	"""Limit Django users to a specific group"""
	class Meta(Model.Meta):
		db_table="rainman_userforgroup"
	def __unicode__(self):
		return u"‹%s @%s %s›" % (self.__class__.__name__,self.user.username,self.group.name)
	user = m.OneToOneField(DjangoUser)
	group = m.ForeignKey(Group, blank=True,null=True, related_name="users",help_text="A group containing the valves this user may access")
	LEVEL_VALUES = (
		('0',"None"),
		('1',"read"),
		('2',"change schedule"),
		('3',"admin"),
	)
	level = m.IntegerField(choices=LEVEL_VALUES,default=1,help_text=u"Access to …")


# definition of UserProfile from above
# ...

def create_user_profile(sender, instance, created, **kwargs):
	if created:
		UserForGroup.objects.create(user=instance)

post_save.connect(create_user_profile, sender=DjangoUser)

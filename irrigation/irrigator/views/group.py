# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

from django.views.generic import ListView,DetailView,CreateView,UpdateView,DeleteView
from django.forms import ModelForm
from rainman.models import Group,Site
from irrigator.views import FormMixin,SiteParamMixin,get_profile
from rainman.utils import get_request

class GroupForm(ModelForm):
	class Meta:
		model = Group
		exclude = ('site',)

	def save(self,commit=True):
		if self.instance.id is None:
			self.instance.site = self.aux_data['site']
		return super(GroupForm,self).save(commit)

	def limit_choices(self,site=None,valve=None):
		gu = get_profile(get_request())
		v = gu.all_valves

		if valve is not None:
			v = v.filter(id=valve.id)
		if site is not None:
			v = v.filter(controller__site__id=site.id)
		self.fields['valves'].queryset = v

class GroupMixin(FormMixin):
	model = Group
	context_object_name = "group"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(GroupMixin,self).get_queryset().filter(id__in=gu.groups)

class GroupsView(GroupMixin,SiteParamMixin,ListView):
	context_object_name = "group_list"
	pass

class GroupView(GroupMixin,DetailView):
	pass

class GroupNewView(GroupMixin,SiteParamMixin,CreateView):
	form_class = GroupForm
	success_url="/group/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(GroupNewView,self).get_form(form_class)
		form.limit_choices(**self.aux_data)
		return form

class GroupEditView(GroupMixin,SiteParamMixin,UpdateView):
	form_class = GroupForm
	success_url="/group/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(GroupEditView,self).get_form(form_class)
		form.limit_choices(**self.aux_data)
		return form

class GroupDeleteView(GroupMixin,DeleteView):
	def post(self,*a,**k):
		group = self.get_object()
		self.success_url="/site/%d" % (group.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


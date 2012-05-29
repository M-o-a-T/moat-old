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
from django.views.generic import ListView,DetailView,CreateView,UpdateView,DeleteView
from django.forms import ModelForm
from rainman.models import ParamGroup,Site
from irrigator.views import FormMixin

class ParamGroupForm(ModelForm):
	class Meta:
		model = ParamGroup
		exclude = ('site',)

	def save(self,commit=True):
		if hasattr(self,'site'):
			self.instance.site = self.site
		return super(ParamGroupForm,self).save(commit)


class ParamGroupMixin(FormMixin):
	model = ParamGroup
	context_object_name = "param_group"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(ParamGroupMixin,self).get_queryset().filter(id__in=gu.param_groups)

class ParamGroupsView(ParamGroupMixin,ListView):
	context_object_name = "param_group_list"
	pass

class ParamGroupView(ParamGroupMixin,DetailView):
	pass

class ParamGroupNewView(ParamGroupMixin,CreateView):
	form_class = ParamGroupForm
	success_url="/params/%(id)s"
	def get_form(self, form_class):
		form = super(ParamGroupNewView,self).get_form(form_class)
		form.site=self.site
		return form
	def get(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ParamGroupNewView,self).get(request,**k)
	def post(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ParamGroupNewView,self).post(request,**k)


class ParamGroupEditView(ParamGroupMixin,UpdateView):
	form_class = ParamGroupForm
	success_url="/param_group/%(id)s"

class ParamGroupDeleteView(ParamGroupMixin,DeleteView):
	def post(self,*a,**k):
		param_group = self.get_object()
		self.success_url="/site/%d" % (param_group.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


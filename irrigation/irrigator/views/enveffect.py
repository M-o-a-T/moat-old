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
from rainman.models import ParamGroup,EnvironmentEffect
from irrigator.views import FormMixin

class EnvEffectForm(ModelForm):
	class Meta:
		model = EnvironmentEffect
		exclude = ('param_group',)

	def save(self,commit=True):
		if hasattr(self,'param_group'):
			self.instance.param_group = self.param_group
		return super(EnvEffectForm,self).save(commit)


class EnvEffectMixin(FormMixin):
	model = EnvironmentEffect
	context_object_name = "enveffect"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(EnvEffectMixin,self).get_queryset().filter(param_group__site__id__in=gu.sites.all())

class EnvEffectsView(EnvEffectMixin,ListView):
	context_object_name = "enveffect_list"
	pass

class EnvEffectView(EnvEffectMixin,DetailView):
	pass

class EnvEffectNewView(EnvEffectMixin,CreateView):
	form_class = EnvEffectForm
	success_url="/environ/%(id)s"
	def get_form(self, form_class):
		form = super(EnvEffectNewView,self).get_form(form_class)
		form.param_group=self.param_group
		return form
	def get(self,request,param,**k):
		self.param_group = ParamGroup.objects.get(id=param)
		return super(EnvEffectNewView,self).get(request,**k)
	def post(self,request,param,**k):
		self.param_group = ParamGroup.objects.get(id=param)
		return super(EnvEffectNewView,self).post(request,**k)


class EnvEffectEditView(EnvEffectMixin,UpdateView):
	form_class = EnvEffectForm
	success_url="/environ/%(id)s"

class EnvEffectDeleteView(EnvEffectMixin,DeleteView):
	def post(self,*a,**k):
		enveffect = self.get_object()
		self.success_url="/params/%d" % (enveffect.param_group.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


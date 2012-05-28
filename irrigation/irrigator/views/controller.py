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
from rainman.models import Controller,Site
from irrigator.views import FormMixin

class ControllerForm(ModelForm):
	class Meta:
		model = Controller
		exclude = ('site',)

	def save(self,commit=True):
		self.instance.site = self.site
		return super(ControllerForm,self).save(commit)


class ControllerMixin(FormMixin):
	model = Controller
	context_object_name = "controller"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(ControllerMixin,self).get_queryset().filter(id__in=gu.controllers)

class ControllersView(ControllerMixin,ListView):
	context_object_name = "controller_list"
	pass

class ControllerView(ControllerMixin,DetailView):
	pass

class ControllerNewView(ControllerMixin,CreateView):
	form_class = ControllerForm
	success_url="/controller/%(id)s"
	def get_form(self, form_class):
		form = super(ControllerNewView,self).get_form(form_class)
		form.site=self.site
		return form
	def get(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ControllerNewView,self).get(request,**k)
	def post(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ControllerNewView,self).post(request,**k)
	def _post_clean(self):
		super(DbModelForm,self)._post_clean()
		self.instance.site = self.site


class ControllerEditView(ControllerMixin,UpdateView):
	form_class = ControllerForm
	success_url="/controller/%(id)s"

class ControllerDeleteView(ControllerMixin,DeleteView):
	def post(self,*a,**k):
		controller = self.get_object()
		self.success_url="/site/%d" % (controller.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


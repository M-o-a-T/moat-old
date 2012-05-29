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
from rainman.models import Valve,Site
from rainman.utils import get_request
from irrigator.views import FormMixin

class ValveForm(ModelForm):
	class Meta:
		model = Valve
		exclude = ('site',)

	def limit_choices(self,site):
		self.site = site
		gu = get_request().user.get_profile()
		self.fields['controller'].queryset = gu.controllers.filter(site=site)
		self.fields['feed'].queryset = gu.feeds.filter(site=site)


class ValveMixin(FormMixin):
	model = Valve
	context_object_name = "valve"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(ValveMixin,self).get_queryset().filter(id__in=gu.all_valves)

class ValvesView(ValveMixin,ListView):
	context_object_name = "valve_list"
	pass

class ValveView(ValveMixin,DetailView):
	pass

# set ModelChoiceField.queryset
class ValveNewView(ValveMixin,CreateView):
	form_class = ValveForm
	success_url="/valve/%(id)s"
	def get_form(self, form_class):
		form = super(ValveNewView,self).get_form(form_class)
		form.limit_choices(self.site)
		return form
	def get(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ValveNewView,self).get(request,**k)
	def post(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(ValveNewView,self).post(request,**k)


class ValveEditView(ValveMixin,UpdateView):
	form_class = ValveForm
	success_url="/valve/%(id)s"
	def get_form(self, form_class):
		form = super(ValveEditView,self).get_form(form_class)
		form.limit_choices(self.site)
		return form
	def get(self,request,pk,**k):
		valve = Valve.objects.get(pk=pk)
		self.site = valve.feed.site
		return super(ValveEditView,self).get(request,pk=pk,**k)
	def post(self,request,pk,**k):
		valve = Valve.objects.get(pk=pk)
		self.site = valve.feed.site
		return super(ValveEditView,self).post(request,pk=pk,**k)

class ValveDeleteView(ValveMixin,DeleteView):
	def post(self,*a,**k):
		valve = self.get_object()
		self.success_url="/site/%d" % (valve.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


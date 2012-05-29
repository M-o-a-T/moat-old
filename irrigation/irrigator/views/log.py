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
from rainman.models import Log,Site,Controller,Valve
from irrigator.views import FormMixin,SiteParamMixin

class LogForm(ModelForm):
	class Meta:
		model = Log
		exclude = ('site',)

	def save(self,commit=True):
		if hasattr(self,'site'):
			self.instance.site = self.site
		return super(LogForm,self).save(commit)

class MoreParamMixin(SiteParamMixin):
	opt_params = {'site':Site, 'controller':Controller, 'valve':Valve}
	def get_params_hook(self):
		super(MoreParamMixin,self).get_params_hook()
		if self.valve is not None:
			#self.controller = self.valve.controller
			self.controller = Valve.objects.get(pk=self.valve).controller.id
		if self.controller is not None:
			#self.site = self.controller.site
			self.site = Controller.objects.get(pk=self.controller).site.id

class LogMixin(FormMixin):
	model = Log
	context_object_name = "log"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(LogMixin,self).get_queryset().filter(site__id__in=gu.sites.all()).order_by("-timestamp")

class LogsView(LogMixin,MoreParamMixin,ListView):
	context_object_name = "log_list"
	paginate_by = 50

class LogView(LogMixin,MoreParamMixin,DetailView):
	def get_context_data(self,**k):
		ctx = super(LogView,self).get_context_data(**k)
		try:
			ctx['next_l'] = self.get_queryset().filter(timestamp__gt=ctx['log'].timestamp).order_by('timestamp')[0]
		except IndexError:
			ctx['next_l'] = None
		try:
			ctx['prev_l'] = self.get_queryset().filter(timestamp__lt=ctx['log'].timestamp).order_by('-timestamp')[0]
		except IndexError:
			ctx['prev_l'] = None
		return ctx


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
from rainman.models import Level,Valve
from irrigator.views import FormMixin,SiteParamMixin
from rainman.utils import now

class LevelForm(ModelForm):
	class Meta:
		model = Level
		exclude = ('forced','time','valve')

	def save(self,commit=True):
		if self.instance.id is None:
			self.instance.time = now()
		self.instance.forced = True
		return super(LevelForm,self).save(commit)


class LevelMixin(FormMixin):
	model = Level
	context_object_name = "level"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(LevelMixin,self).get_queryset().filter(valve__in=gu.all_valves).order_by('-time')

class LevelsView(LevelMixin,SiteParamMixin,ListView):
	context_object_name = "level_list"
	opt_params = {'valve':Valve}
	paginate_by=50

class LevelView(LevelMixin,DetailView):
	def get_context_data(self,**k):
		ctx = super(LevelView,self).get_context_data(**k)
		try:
			ctx['next_lv'] = self.get_queryset().filter(time__gt=ctx['level'].time).order_by('time')[0]
		except IndexError:
			ctx['next_lv'] = None
		try:
			ctx['prev_lv'] = self.get_queryset().filter(time__lt=ctx['level'].time).order_by('-time')[0]
		except IndexError:
			ctx['prev_lv'] = None
		return ctx


class LevelNewView(LevelMixin,SiteParamMixin,CreateView):
	form_class = LevelForm
	success_url="/level/%(id)s"
	opt_params = {'valve':Valve}

class LevelEditView(LevelMixin,UpdateView):
	form_class = LevelForm
	success_url="/level/%(id)s"



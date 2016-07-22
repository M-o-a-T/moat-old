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
from django.forms import ModelForm,ModelMultipleChoiceField
from django.http import Http404
from rainman.models import Valve,Site, Controller,Feed,EnvGroup,Group
from rainman.utils import get_request
from irrigator.views import FormMixin,SiteParamMixin,get_profile, TimeDeltaField

class ValveForm(ModelForm):
	class Meta:
		model = Valve
		exclude = ('site','db_max_run','db_min_delay')
		fields = ('name','comment','controller','feed','envgroup','location','var','verbose','flow','area','max_level','start_level','stop_level','max_run','min_delay','shade','runoff','time','level','priority','groups')
		#many_to_many = ('groups,')

	max_run = TimeDeltaField(required=False,help_text=Meta.model._meta.get_field("db_max_run").help_text)
	min_delay = TimeDeltaField(required=False,help_text=Meta.model._meta.get_field("db_min_delay").help_text)

	#groups = ModelMultipleChoiceField(queryset=Group.objects.all())

	def limit_choices(self,site=None,controller=None,feed=None,envgroup=None):
		gu = get_profile(get_request())
		if feed is not None:
			self.fields['feed'].queryset = gu.feeds.filter(id=feed.id)
		elif site is not None:
			self.fields['feed'].queryset = gu.feeds.filter(site=site)

		if controller is not None:
			self.fields['controller'].queryset = gu.controllers.filter(id=controller.id)
		elif site is not None:
			self.fields['controller'].queryset = gu.controllers.filter(site=site)

		if envgroup is not None:
			self.fields['envgroup'].queryset = gu.envgroups.filter(id=envgroup.id)
		elif site is not None:
			self.fields['envgroup'].queryset = gu.envgroups.filter(site=site)

		if site is not None:
			self.fields['groups'].queryset = gu.groups.filter(site=site)
		else:
			self.fields['groups'].queryset = gu.groups ## should not happen
	

class ValveMixin(FormMixin):
	model = Valve
	context_object_name = "valve"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(ValveMixin,self).get_queryset().filter(id__in=gu.all_valves)

class ValveParamMixin(SiteParamMixin):
	opt_params = {'controller':Controller, 'feed':Feed, 'site':Site, 'envgroup':EnvGroup}

	def get_params_hook(self,*a,**k):
		super(ValveParamMixin,self).get_params_hook(*a,**k)
		s = self.aux_data['site']
		c = self.aux_data['controller']
		f = self.aux_data['feed']
		eg = self.aux_data['envgroup']
		if s:
			if c is not None and s != c.site:
				raise Http404
			if f is not None and s != f.site:
				raise Http404
		elif c:
			if f is not None and c.site != f.site:
				raise Http404
			self.aux_data['site'] = c.site
		elif f:
			self.aux_data['site'] = f.site
		if eg:
			if self.aux_data['site'] is None:
				self.aux_data['site'] = eg.site
			elif self.aux_data['site'] != eg.site:
				raise Http404

	def get_form_kwargs(self):
		args = super(ValveParamMixin,self).get_form_kwargs()
		obj = args.get('instance',None)
		if obj is None:
			args['initial'] = self.aux_data.copy()
#		else:
#			args['initial']['groups'] = (x.id for x in obj.groups.all())

		return args

class ValvesView(ValveMixin,ValveParamMixin,ListView):
	context_object_name = "valve_list"
	pass

class ValveView(ValveMixin,DetailView):
	pass

# set ModelChoiceField.queryset
class ValveNewView(ValveMixin,ValveParamMixin,CreateView):
	form_class = ValveForm
	success_url="/valve/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(ValveNewView,self).get_form(form_class)
		form.limit_choices(**self.aux_data)
		return form

class ValveEditView(ValveMixin,ValveParamMixin,UpdateView):
	form_class = ValveForm
	success_url="/valve/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(ValveEditView,self).get_form(form_class)
		form.limit_choices(site=self.site)
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
		self.success_url="/site/%d" % (valve.controller.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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
from rainman.models import ValveOverride,Site,Controller,Valve,Feed,EnvGroup
from irrigator.views import DbModelForm,FormMixin,SiteParamMixin,TimeDeltaField,get_profile
from rainman.utils import get_request

def limit_choices(q,site=None,controller=None,envgroup=None,valve=None,feed=None):
	if site is not None:
		q = q.filter(controller__site=site)
	if controller is not None:
		q = q.filter(controller=controller)
	if feed is not None:
		q = q.filter(feed=feed)
	if envgroup is not None:
		q = q.filter(envgroup=envgroup)
	if valve is not None:
		q = q.filter(id__exact=valve.id)
	return q

class ValveOverrideForm(DbModelForm):
	class Meta:
		model = ValveOverride
		exclude = ('db_duration',)
		fields = ('name','valve','start','duration','running')

	# 'Excluded' fields
	duration = TimeDeltaField(help_text=Meta.model._meta.get_field("db_duration").help_text)

	def limit_choices(self,**k):
		gu = get_profile(get_request())

		self.fields['valve'].queryset = limit_choices(gu.all_valves,**k)

class ValveOverrideParamMixin(SiteParamMixin):
	opt_params = {'site':Site, 'controller':Controller, 'valve':Valve, 'feed': Feed, 'envgroup':EnvGroup, 'valve':Valve}
	opt_names = { 'envgroup': 'valve__envgroup', 'site':'valve__controller__site','controller':'valve__controller','feed':'valve__feed' }

	def get_params_hook(self,*a,**k):
		super(ValveOverrideParamMixin,self).get_params_hook(*a,**k)
		s = self.aux_data['site']
		c = self.aux_data['controller']
		f = self.aux_data['feed']
		eg = self.aux_data['envgroup']
		v = self.aux_data['valve']
		if v:
			if c is not None and v.controller != c:
				raise Http404
			if f is not None and v.feed != f:
				raise Http404
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

class ValveOverrideMixin(FormMixin):
	model = ValveOverride
	context_object_name = "valveoverride"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(ValveOverrideMixin,self).get_queryset().filter(valve__controller__site__id__in=gu.sites.all()).order_by("-start")

	def get_context_data(self,**k):
		ctx = super(ValveOverrideMixin,self).get_context_data(**k)
		s=self.aux_data.get('site',None)
		c=self.aux_data.get('controller',None)
		f=self.aux_data.get('feed',None)
		eg=self.aux_data.get('envgroup',None)
		v=self.aux_data.get('valve',None)
		if v is not None:
			prefix = "/valve/%s/time" % (v.id,)
		elif eg is not None:
			prefix = "/envgroup/%s/time" % (eg.id,)
		elif f is not None:
			prefix = "/feed/%s/time" % (f.id,)
		elif c is not None:
			prefix = "/controller/%s/time" % (c.id,)
		elif s is not None:
			prefix = "/site/%s/time" % (s.id,)
		else:
			prefix = "/valve/time" 
		ctx['prefix'] = prefix
		return ctx

class ValveOverridesView(ValveOverrideMixin,ValveOverrideParamMixin,ListView):
	context_object_name = "valveoverride_list"
	paginate_by = 50

class ValveOverrideView(ValveOverrideMixin,ValveOverrideParamMixin,DetailView):
	def get_context_data(self,**k):
		ctx = super(ValveOverrideView,self).get_context_data(**k)
		gu = get_profile(get_request())
		av = limit_choices(gu.all_valves,**self.aux_data)
		q = ValveOverride.objects.filter(valve__in=av)
		try:
			ctx['next_s'] = q.filter(start__gt=ctx['valveoverride'].start).order_by('start')[0]
		except IndexError:
			ctx['next_s'] = None
		try:
			ctx['prev_s'] = q.filter(start__lt=ctx['valveoverride'].start).order_by('-start')[0]
		except IndexError:
			ctx['prev_s'] = None
		return ctx

# set ModelChoiceField.queryset
class ValveOverrideNewView(ValveOverrideMixin,ValveOverrideParamMixin,CreateView):
	form_class = ValveOverrideForm
	success_url="/valve/time/%(id)s"
	#success_url="/valve/%(valve)s/time/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(ValveOverrideNewView,self).get_form(form_class)
		form.limit_choices(**self.aux_data)
		return form
	def get_form_kwargs(self):
		args = super(ValveOverrideNewView,self).get_form_kwargs()
		if args.get('instance',None) is None:
			args['initial'] = self.aux_data.copy()
		return args
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']+"/"+str(self.object.id)

class ValveOverrideEditView(ValveOverrideMixin,ValveOverrideParamMixin,UpdateView):
	form_class = ValveOverrideForm
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(ValveOverrideEditView,self).get_form(form_class)
		form.limit_choices(valve=self.object.valve)
		return form
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']+"/"+str(self.object.id)

class ValveOverrideDeleteView(ValveOverrideMixin,ValveOverrideParamMixin,DeleteView):
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']


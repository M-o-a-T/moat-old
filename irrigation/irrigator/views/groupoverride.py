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
from rainman.models import GroupOverride,Site,Group,Group
from irrigator.views import DbModelForm,FormMixin,SiteParamMixin,TimeDeltaField,get_profile
from rainman.utils import get_request

def limit_choices(q,site=None,group=None):
	if site is not None:
		q = q.filter(site=site)
	if group is not None:
		q = q.filter(id__exact=group.id)
	return q

class GroupOverrideForm(DbModelForm):
	class Meta:
		model = GroupOverride
		exclude = ('db_duration',)
		fields = ('name','group','start','duration','allowed')

	# 'Excluded' fields
	duration = TimeDeltaField(help_text=Meta.model._meta.get_field_by_name("db_duration")[0].help_text)

	def limit_choices(self,**k):
		gu = get_profile(get_request())

		self.fields['group'].queryset = limit_choices(gu.groups,**k)

class GroupOverrideParamMixin(SiteParamMixin):
	opt_params = {'site':Site, 'group':Group}
	opt_names = { 'site':'group__site' }

	def get_params_hook(self,*a,**k):
		super(GroupOverrideParamMixin,self).get_params_hook(*a,**k)
		s = self.aux_data['site']
		g = self.aux_data['group']
		if s:
			if g is not None and s != g.site:
				raise Http404
		elif g:
			self.aux_data['site'] = g.site

class GroupOverrideMixin(FormMixin):
	model = GroupOverride
	context_object_name = "groupoverride"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(GroupOverrideMixin,self).get_queryset().filter(group__site__id__in=gu.sites.all()).order_by("-start")

	def get_context_data(self,**k):
		ctx = super(GroupOverrideMixin,self).get_context_data(**k)
		s=self.aux_data.get('site',None)
		g=self.aux_data.get('group',None)
		if g is not None:
			prefix = "/group/%s/time" % (g.id,)
		elif s is not None:
			prefix = "/site/%s/gtime" % (s.id,)
		else:
			prefix = "/group/time" 
		ctx['prefix'] = prefix
		return ctx

class GroupOverridesView(GroupOverrideMixin,GroupOverrideParamMixin,ListView):
	context_object_name = "groupoverride_list"
	paginate_by = 50

class GroupOverrideView(GroupOverrideMixin,GroupOverrideParamMixin,DetailView):
	def get_context_data(self,**k):
		ctx = super(GroupOverrideView,self).get_context_data(**k)
		gu = get_profile(get_request())
		av = limit_choices(gu.groups,**self.aux_data)
		q = GroupOverride.objects.filter(group__in=av)
		try:
			ctx['next_s'] = q.filter(start__gt=ctx['groupoverride'].start).order_by('start')[0]
		except IndexError:
			ctx['next_s'] = None
		try:
			ctx['prev_s'] = q.filter(start__lt=ctx['groupoverride'].start).order_by('-start')[0]
		except IndexError:
			ctx['prev_s'] = None
		return ctx

# set ModelChoiceField.queryset
class GroupOverrideNewView(GroupOverrideMixin,GroupOverrideParamMixin,CreateView):
	form_class = GroupOverrideForm
	success_url="/group/time/%(id)s"
	#success_url="/group/%(group)s/time/%(id)s"
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(GroupOverrideNewView,self).get_form(form_class)
		form.limit_choices(**self.aux_data)
		return form
	def get_form_kwargs(self):
		args = super(GroupOverrideNewView,self).get_form_kwargs()
		if args.get('instance',None) is None:
			args['initial'] = self.aux_data.copy()
		return args
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']+"/"+str(self.object.id)

class GroupOverrideEditView(GroupOverrideMixin,GroupOverrideParamMixin,UpdateView):
	form_class = GroupOverrideForm
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.form_class
		form = super(GroupOverrideEditView,self).get_form(form_class)
		form.limit_choices(group=self.object.group)
		return form
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']+"/"+str(self.object.id)

class GroupOverrideDeleteView(GroupOverrideMixin,GroupOverrideParamMixin,DeleteView):
	def get_success_url(self):
		ctx = self.get_context_data()
		return ctx['prefix']


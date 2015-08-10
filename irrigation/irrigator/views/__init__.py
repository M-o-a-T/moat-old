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
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ModelForm,FloatField,TimeField
from django.utils.translation import ugettext_lazy as _
from django.template.context_processors import csrf
from datetime import timedelta,datetime

from rainman.models import Site
#from rainman.utils import Redirect

def get_profile(request):
	try:
		gu = request.user.profile
	except (ObjectDoesNotExist,AttributeError):
		if request.user.is_authenticated():
			raise Redirect('/login/no_access')
		else:
			raise Redirect('/login/?next=%s' % request.path)
	else:
		return gu

def home(request):
	try:
		gu = request.user.get_profile()
	except (ObjectDoesNotExist,AttributeError):
		sites = set()
	else:
		sites = gu.sites.all()

	if not sites:
		if request.user.is_authenticated():
			return HttpResponseRedirect('/login/no_access')
		else:
			return HttpResponseRedirect('/login/?next=%s' % request.path)

	if len(sites) == 1:
		return HttpResponseRedirect('/site/%d' % list(sites)[0].id)

	return HttpResponseRedirect('/site/')

class NonNegativeFloatField(FloatField):
	def clean(self,val):
		val = super(NonNegativeFloatField,self).clean(val)
		if val < 0:
			raise ValidationError(_(u'must not be negative'))
		return val

def Delta(t):
	if t is None:
		return None
	if isinstance(t,timedelta):
		return t
	return timedelta(0,(t.hour*60+t.minute)*60+t.second,t.microsecond)

class TimeDeltaField(TimeField):
	default_error_messages = {
		'invalid': _(u'Enter a valid time interval.')
	}

	def to_python(self, value):
		"""
		Validates that the input can be converted to a time. Returns a Python
		datetime.timedelta object.
		"""
		res = super(TimeDeltaField, self).to_python(value)
		return Delta(res)

	def strptime(self, value, format):
		return Delta(datetime.strptime(value, format).time())

class FormMixin(object):
	def get_template_names(self):
		return ["obj/%s/%s.jinja" % (self.model._meta.object_name.lower(), self.template_name_suffix.lstrip("_"))]

class SiteParamMixin(object):
	opt_params = {'site':Site}
	opt_names = {}
	def __init__(self,*a,**k):
		super(SiteParamMixin,self).__init__(*a,**k)
		self.aux_data = {}

	def get_params_hook(self,request,k):
		for p,d in self.opt_params.items():
			pk = k.get(p,None)
			if pk is not None:
				self.aux_data[p] = d.objects.get(pk=k.pop(p))
			else:
				self.aux_data[p] = None
		self.aux_data.update(csrf(request))

	def get_form(self, form_class=None):
		if form_class is None:
			form_class = getattr(self,'form_class',None)
		form = super(SiteParamMixin,self).get_form(form_class)
		form.aux_data = self.aux_data
		return form

	def get(self, request, **k):
		self.get_params_hook(request,k)
		return super(SiteParamMixin,self).get(request,**k)
	def post(self,request,**k):
		self.get_params_hook(request,k)
		return super(SiteParamMixin,self).post(request,**k)

	def get_queryset(self):
		q = super(SiteParamMixin,self).get_queryset()
		f = {}
		for p,v in self.aux_data.items():
			if p in self.opt_names:
				p = self.opt_names[p]
			if v is not None:
				f[p] = v
		f.pop('csrf_token',None)
		if f:
			q = q.filter(**f)
		return q

	def get_context_data(self,**k):
		ctx = super(SiteParamMixin,self).get_context_data(**k)
		for p,v in self.aux_data.items():
			if v is not None:
				ctx[p] = v
		return ctx

class DbModelForm(ModelForm):
	def __init__(self,instance=None,initial=None,*a,**k):
		opts = self._meta
		if instance is None:
			instance = opts.model()
		if initial is None:
			initial = {}
		for fn in self.Meta.exclude:
			if not fn.startswith("db_"): continue
			fn = fn[3:]
			if fn not in initial:
				initial[fn] = getattr(instance,fn)

		k['initial'] = initial
		k['instance'] = instance
		super(DbModelForm,self).__init__(*a,**k)

	def save(self,commit=True):
		for fn in self.Meta.exclude:
			if not fn.startswith("db_"): continue
			fn = fn[3:]
			setattr(self.instance,fn, self.cleaned_data[fn])
		return super(DbModelForm,self).save(commit)


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
from django.utils.translation import ugettext_lazy as _
from rainman.models import Site
from rainman.utils import get_request
from datetime import time
from irrigator.views import NonNegativeFloatField,TimeDeltaField,FormMixin,DbModelForm,get_profile

class SiteForm(DbModelForm):
	class Meta:
		model = Site
		exclude = ('db_rate','db_rain_delay')
		fields = ('name','comment','var','host','rain_delay','rate')
	
	# 'Excluded' fields
	rate = NonNegativeFloatField(help_text=Meta.model._meta.get_field_by_name("db_rate")[0].help_text)
	rain_delay = TimeDeltaField(help_text=Meta.model._meta.get_field_by_name("db_rain_delay")[0].help_text)

	def save(self,commit=True):
		r = super(SiteForm,self).save(commit)
		gu = get_profile(get_request())
		gu.sites.add(r)
		gu.save() ## TODO: check if 'commit' is True!
		return r
	
class SiteMixin(FormMixin):
	model = Site
	context_object_name = "site"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(SiteMixin,self).get_queryset().filter(id__in=gu.sites.all())

class SitesView(SiteMixin,ListView):
	context_object_name = "site_list"

class SiteView(SiteMixin,DetailView):
	pass

class SiteNewView(SiteMixin,CreateView):
	form_class = SiteForm
	success_url="/site/%(id)s"

class SiteEditView(SiteMixin,UpdateView):
	form_class = SiteForm
	success_url="/site/%(id)s"

class SiteDeleteView(SiteMixin,DeleteView):
	success_url="/site/"


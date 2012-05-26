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
from django.shortcuts import get_object_or_404
from django.views.generic import ListView,DetailView,CreateView,UpdateView,DeleteView
from django.forms import ModelForm,FloatField,TimeField,Textarea
from rainman.models import Site


def home(request):
	try:
		gu = request.user.get_profile()
	except (ObjectDoesNotExist,AttributeError):
		sites = set()
	else:
		sites = gu.sites

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
			raise ValidationError("must not be negative")
		return val

class BasicSiteForm(ModelForm):
    class Meta:
        model = Site
#class SiteForm(BasicSiteForm):
class SiteForm(ModelForm):
	#class Meta(BasicSiteForm.Meta):
	class Meta:
		model = Site
		exclude = ('db_rate','db_rain_delay')
		fields = ('name','var','host','rain_delay','rate')
		widgets = {
			'name': Textarea(attrs={'cols': 80, 'rows': 20}),
		}
	rate = NonNegativeFloatField(help_text=Meta.model._meta.get_field_by_name("db_rate")[0].help_text)
	rain_delay = TimeField(help_text=Meta.model._meta.get_field_by_name("db_rain_delay")[0].help_text)

	def construct_instance(form, instance, fields=None, exclude=None):
		instance = super(SiteForm,self).construct_instance(form,instance,fields,exclude)
		for fn in self.Meta.exclude:
			if not fn.startswith("db_"): continue
			fn = fn[3:]
			setattr(instance,fn, form.cleaned_data[fn])
	

# Creating a form to add an article.
form = SiteForm()

# Creating a form to change an existing article.
#site = Site.objects.get(pk=1)
#form = SiteForm(instance=site)



class SiteMixin(object):
	model = Site
	context_object_name = "site"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(SiteMixin,self).get_queryset().filter(id__in=(x.id for x in gu.sites))
	def get_template_names(self):
		return ["obj/%s%s.jinja" % (self.model._meta.object_name.lower(), self.template_name_suffix)]

class SitesView(SiteMixin,ListView):
	context_object_name = "site_list"
	pass

class SiteView(SiteMixin,DetailView):
	pass

class SiteNewView(SiteMixin,CreateView):
	success_url="/site/%(id)s"

class SiteEditView(SiteMixin,UpdateView):
	success_url="/site/%(id)s"

class SiteDeleteView(SiteMixin,DeleteView):
	pass


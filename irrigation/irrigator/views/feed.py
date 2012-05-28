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
from rainman.models import Feed,Site
from irrigator.views import TimeDeltaField,FormMixin,DbModelForm

class FeedForm(DbModelForm):
	class Meta:
		model = Feed
		exclude = ('db_max_flow_wait','site')
		fields = ('name','var','flow','max_flow_wait')

	max_flow_wait = TimeDeltaField(help_text=Meta.model._meta.get_field_by_name("db_max_flow_wait")[0].help_text)

	def save(self,commit=True):
		if hasattr(self,'site'):
			self.instance.site = self.site
		return super(FeedForm,self).save(commit)


class FeedMixin(FormMixin):
	model = Feed
	context_object_name = "feed"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(FeedMixin,self).get_queryset().filter(id__in=gu.feeds)

class FeedsView(FeedMixin,ListView):
	context_object_name = "feed_list"
	pass

class FeedView(FeedMixin,DetailView):
	pass

class FeedNewView(FeedMixin,CreateView):
	form_class = FeedForm
	success_url="/feed/%(id)s"
	def get_form(self, form_class):
		form = super(FeedNewView,self).get_form(form_class)
		form.site=self.site
		return form
	def get(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(FeedNewView,self).get(request,**k)
	def post(self,request,site,**k):
		self.site = Site.objects.get(id=site)
		return super(FeedNewView,self).post(request,**k)

class FeedEditView(FeedMixin,UpdateView):
	form_class = FeedForm
	success_url="/feed/%(id)s"

class FeedDeleteView(FeedMixin,DeleteView):
	def post(self,*a,**k):
		feed = self.get_object()
		self.success_url="/site/%d" % (feed.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


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
from rainman.models import Feed,Site
from irrigator.views import TimeDeltaField,FormMixin,DbModelForm,SiteParamMixin,get_profile

class FeedForm(DbModelForm):
	class Meta:
		model = Feed
		exclude = ('db_max_flow_wait','site')
		fields = ('name','comment','var','flow','max_flow_wait','disabled')

	max_flow_wait = TimeDeltaField(help_text=Meta.model._meta.get_field("db_max_flow_wait").help_text)

	def save(self,commit=True):
		if self.instance.id is None:
			self.instance.site = self.aux_data['site']
		return super(FeedForm,self).save(commit)

class FeedMixin(FormMixin):
	model = Feed
	context_object_name = "feed"
	def get_queryset(self):
		gu = get_profile(self.request)
		return super(FeedMixin,self).get_queryset().filter(id__in=gu.feeds)

class FeedsView(FeedMixin,SiteParamMixin,ListView):
	context_object_name = "feed_list"
	pass

class FeedView(FeedMixin,DetailView):
	pass

class FeedNewView(FeedMixin,SiteParamMixin,CreateView):
	form_class = FeedForm
	success_url="/feed/%(id)s"

class FeedEditView(FeedMixin,UpdateView):
	form_class = FeedForm
	success_url="/feed/%(id)s"

class FeedDeleteView(FeedMixin,DeleteView):
	def post(self,*a,**k):
		feed = self.get_object()
		self.success_url="/site/%d" % (feed.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


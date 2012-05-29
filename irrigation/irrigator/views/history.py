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
from rainman.models import History,Site
from irrigator.views import FormMixin

class HistoryForm(ModelForm):
	class Meta:
		model = History
		exclude = ('site',)

	def save(self,commit=True):
		if hasattr(self,'site'):
			self.instance.site = self.site
		return super(HistoryForm,self).save(commit)


class HistoryMixin(FormMixin):
	model = History
	context_object_name = "history"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(HistoryMixin,self).get_queryset().filter(site__id__in=gu.sites.all())

class HistorysView(HistoryMixin,ListView):
	context_object_name = "history_list"
	paginate_by = 50
	def get(self, request, site=None, **k):
		self.site = site
		return super(HistorysView,self).get(request,**k)
	def get_queryset(self):
		q = super(HistorysView,self).get_queryset()
		if self.site is not None:
			q = q.filter(site=self.site)
		return q.order_by("-time")
	def get_context_data(self,**k):
		ctx = super(HistorysView,self).get_context_data(**k)
		ctx['site'] = self.site
		return ctx

class HistoryView(HistoryMixin,DetailView):
	pass


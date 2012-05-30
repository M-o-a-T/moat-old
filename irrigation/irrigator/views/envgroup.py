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
from rainman.models import EnvGroup,Site
from irrigator.views import FormMixin,SiteParamMixin

class EnvGroupForm(ModelForm):
	class Meta:
		model = EnvGroup
		exclude = ('site',)

	def save(self,commit=True):
		if self.instance.id is None:
			self.instance.site = self.aux_data['site']
		return super(EnvGroupForm,self).save(commit)


class EnvGroupMixin(FormMixin):
	model = EnvGroup
	context_object_name = "envgroup"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(EnvGroupMixin,self).get_queryset().filter(id__in=gu.envgroups)

class EnvGroupsView(EnvGroupMixin,SiteParamMixin,ListView):
	context_object_name = "envgroup_list"

class EnvGroupView(EnvGroupMixin,DetailView):
	pass

class EnvGroupNewView(EnvGroupMixin,SiteParamMixin,CreateView):
	form_class = EnvGroupForm
	success_url="/envgroup/%(id)s"

class EnvGroupEditView(EnvGroupMixin,UpdateView):
	form_class = EnvGroupForm
	success_url="/envgroup/%(id)s"

class EnvGroupDeleteView(EnvGroupMixin,DeleteView):
	def post(self,*a,**k):
		envgroup = self.get_object()
		self.success_url="/site/%d" % (envgroup.site.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


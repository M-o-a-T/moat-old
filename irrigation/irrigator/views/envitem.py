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
from rainman.models import EnvGroup,EnvItem
from irrigator.views import FormMixin,SiteParamMixin

class EnvItemForm(ModelForm):
	class Meta:
		model = EnvItem
		exclude = ('group',)

	def save(self,commit=True):
		if self.instance.id is None:
			self.instance.group = self.aux_data['group']
		return super(EnvItemForm,self).save(commit)


class EnvItemMixin(FormMixin):
	model = EnvItem
	context_object_name = "envitem"
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(EnvItemMixin,self).get_queryset().filter(group__site__id__in=gu.sites.all())

class EnvParamMixin(SiteParamMixin):
	opt_params = {'group':EnvGroup}

class EnvItemsView(EnvItemMixin,EnvParamMixin,ListView):
	context_object_name = "envitem_list"
	pass

class EnvItemView(EnvItemMixin,DetailView):
	pass

class EnvItemNewView(EnvItemMixin,EnvParamMixin,CreateView):
	form_class = EnvItemForm
	success_url="/envitem/%(id)s"


class EnvItemEditView(EnvItemMixin,EnvParamMixin,UpdateView):
	form_class = EnvItemForm
	success_url="/envitem/%(id)s"

class EnvItemDeleteView(EnvItemMixin,DeleteView):
	def post(self,*a,**k):
		envitem = self.get_object()
		self.success_url="/envgroup/%d" % (envitem.group.id,)
		return super(DeleteView,self).post(*a,**k)
	pass


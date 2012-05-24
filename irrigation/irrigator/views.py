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
from django.views.generic import ListView,DetailView
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


class SiteLimiter(object):
	model = Site
	def get_queryset(self):
		gu = self.request.user.get_profile()
		return super(SiteLimiter,self).get_queryset().filter(id__in=(x.id for x in gu.sites))

class SitesView(SiteLimiter,ListView):
	context_object_name = "site_list"
	template_name = "obj/sites.jinja"

class SiteView(SiteLimiter,DetailView):
	context_object_name = "site"
	template_name = "obj/site.jinja"

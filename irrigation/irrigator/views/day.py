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
from rainman.models import Day
from rainman.utils import get_request
from datetime import time
from irrigator.views import NonNegativeFloatField,TimeDeltaField,FormMixin,DbModelForm

class DayForm(ModelForm):
	class Meta:
		model = Day
	
class DayMixin(FormMixin):
	model = Day
	context_object_name = "day"

class DaysView(DayMixin,ListView):
	context_object_name = "day_list"

class DayView(DayMixin,DetailView):
	pass

class DayNewView(DayMixin,CreateView):
	form_class = DayForm
	success_url="/day/%(id)s"

class DayEditView(DayMixin,UpdateView):
	form_class = DayForm
	success_url="/day/%(id)s"

class DayDeleteView(DayMixin,DeleteView):
	success_url="/day/"


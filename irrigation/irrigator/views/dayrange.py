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
from rainman.models import DayRange
from rainman.utils import get_request
from datetime import time
from irrigator.views import NonNegativeFloatField,TimeDeltaField,FormMixin,DbModelForm

class DayRangeForm(ModelForm):
	class Meta:
		model = DayRange
	
class DayRangeMixin(FormMixin):
	model = DayRange
	context_object_name = "dayrange"

class DayRangesView(DayRangeMixin,ListView):
	context_object_name = "dayrange_list"

class DayRangeView(DayRangeMixin,DetailView):
	pass

class DayRangeNewView(DayRangeMixin,CreateView):
	form_class = DayRangeForm
	success_url="/dayrange/%(id)s"

class DayRangeEditView(DayRangeMixin,UpdateView):
	form_class = DayRangeForm
	success_url="/dayrange/%(id)s"

class DayRangeDeleteView(DayRangeMixin,DeleteView):
	success_url="/dayrange/"


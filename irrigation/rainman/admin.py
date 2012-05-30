from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman.models import Site,Feed,Controller,Valve,EnvGroup,History,EnvItem,Level,DayRange,Day,DayTime,Group,GroupOverride,ValveOverride,GroupAdjust,Schedule,RainMeter,TempMeter,WindMeter,SunMeter,UserForSite,Log

from rainman.utils import now
from datetime import timedelta

# SiteInline
class FeedInline(admin.TabularInline):
	model = Feed
	extra = 0

class ControllerInline(admin.TabularInline):
	model = Controller
	extra = 0

class ValveInline(admin.StackedInline):
	model = Valve
	extra = 0
	fields = (('name','var','location','feed'),('flow','area','shade','runoff'), ('time','level','priority','comment'),('envgroup','max_level','start_level','stop_level'))

class EnvGroupInline(admin.TabularInline):
	model = EnvGroup
	extra = 0

class HistoryInline(admin.TabularInline):
	model = History
	extra = 0

class EnvItemInline(admin.TabularInline):
	model = EnvItem
	extra = 0

class LevelInline(admin.TabularInline):
	model = Level
	extra = 0
	def queryset(self, request):
		qs = super(LevelInline, self).queryset(request)
		return qs.filter(time__gte = now()-timedelta(1,0)).order_by("-time")

class DayRangeInline(admin.TabularInline):
	model = DayRange
	extra = 0

class DayInline(admin.TabularInline):
	model = Day
	extra = 0

class DayTimeInline(admin.TabularInline):
	model = DayTime
	extra = 0

class GroupInline(admin.TabularInline):
	model = Group
	extra = 0

class GroupOverrideInline(admin.TabularInline):
	model = GroupOverride
	extra = 0
	def queryset(self, request):
		qs = super(GroupOverrideInline, self).queryset(request)
		return qs.filter(start__gte = now()-timedelta(1,0)).order_by("-start")

class ValveOverrideInline(admin.TabularInline):
	model = ValveOverride
	extra = 0
	def queryset(self, request):
		qs = super(ValveOverrideInline, self).queryset(request)
		return qs.filter(start__gte = now()-timedelta(1,0)).order_by("-start")

class EnvGroupInline(admin.TabularInline):
	model = EnvGroup
	extra = 0

class GroupAdjustInline(admin.TabularInline):
	model = GroupAdjust
	extra = 0

class ScheduleInline(admin.TabularInline):
	model = Schedule
	extra = 0
	def queryset(self, request):
		qs = super(ScheduleInline, self).queryset(request)
		return qs.filter(start__gte = now()-timedelta(0.5)).order_by("start")

class RainMeterInline(admin.TabularInline):
	model = RainMeter
	extra = 0

class TempMeterInline(admin.TabularInline):
	model = TempMeter
	extra = 0

class WindMeterInline(admin.TabularInline):
	model = WindMeter
	extra = 0

class SunMeterInline(admin.TabularInline):
	model = SunMeter
	extra = 0

class UserForSiteInline(admin.TabularInline):
	model = UserForSite
	extra = 0

class LogInline(admin.TabularInline):
	model = Log
	extra = 0


class SiteAdmin(admin.ModelAdmin):
	list_display = ('name','host','var')
	inlines = [
		FeedInline,
		ControllerInline,
		GroupInline,
		EnvGroupInline,
		RainMeterInline,
		TempMeterInline,
		WindMeterInline,
		SunMeterInline,
	]

class FeedAdmin(admin.ModelAdmin):
	list_display = ('name','site','flow','var')
	list_filter = ('site',)
	inlines = [
		ValveInline,
	]

class ControllerAdmin(admin.ModelAdmin):
	list_display = ('name','site','location','list_range')
	list_filter = ('site',)
	inlines = [
		ValveInline,
	]

class ValveAdmin(admin.ModelAdmin):
	list_display = ('name','controller','var','comment','time','level','priority','list_groups','adj','flow','area','stop_level','start_level','max_level','watering_time')
	list_filter = ('feed','envgroup','controller')
	inlines = [
		ValveOverrideInline,
		ScheduleInline,
	]

class LevelAdmin(admin.ModelAdmin):
	list_display = ('valve','time','level','flow','forced')
	list_filter = ('valve',)
	date_hierarchy = 'time'
	ordering = ('-time',)

class HistoryAdmin(admin.ModelAdmin):
	list_display = ('time','rain','temp','wind','sun','feed')
	list_filter = ('site',)
	date_hierarchy = 'time'
	ordering = ('-time',)

class EnvItemAdmin(admin.ModelAdmin):
	list_display = ('group','factor','temp','wind','sun')
	list_filter = ('group',)

class DayRangeAdmin(admin.ModelAdmin):
	list_display = ('name','list_range')

class DayAdmin(admin.ModelAdmin):
	list_display = ('name','list_daytimes','list_range')
	inlines = [
		DayTimeInline,
	]

class DayTimeAdmin(admin.ModelAdmin):
	list_display = ('day','descr','list_range')
	list_filter = ('day',)

class GroupAdmin(admin.ModelAdmin):
	list_display = ('name','site','list_valves','list_range')
	fields = ('name','site',('valves','days','xdays','adj'))
	list_filter = ('site',)
	inlines = [
		GroupOverrideInline,
		GroupAdjustInline,
	]

class GroupOverrideAdmin(admin.ModelAdmin):
	list_display = ('group','start','duration','end','allowed')
	list_filter = ('group',)
	date_hierarchy = 'start'
	ordering = ('-start',)

class ValveOverrideAdmin(admin.ModelAdmin):
	list_display = ('valve','start','duration','end','running')
	list_filter = ('valve',)
	date_hierarchy = 'start'
	ordering = ('-start',)

class EnvGroupAdmin(admin.ModelAdmin):
	list_display = ('name','site','factor','list_valves')
	list_filter = ('site',)
	inlines = [
		EnvItemInline,
		#ValveInline,
	]

class GroupAdjustAdmin(admin.ModelAdmin):
	list_display = ('group','start','factor')
	list_filter = ('group',)
	date_hierarchy = 'start'
	ordering = ('-start',)

class ScheduleAdmin(admin.ModelAdmin):
	list_display = ('valve','start','duration','end','seen','changed')
	list_filter = ('valve',)
	date_hierarchy = 'start'
	ordering = ('-start',)

class RainMeterAdmin(admin.ModelAdmin):
	list_display = ('name','var')
	list_filter = ('site',)

class TempMeterAdmin(admin.ModelAdmin):
	list_display = ('name','var')
	list_filter = ('site',)

class WindMeterAdmin(admin.ModelAdmin):
	list_display = ('name','var')
	list_filter = ('site',)

class SunMeterAdmin(admin.ModelAdmin):
	list_display = ('name','var')
	list_filter = ('site',)

class UserForSiteAdmin(admin.ModelAdmin):
	list_display = ('user','level')

class LogAdmin(admin.ModelAdmin):
	list_display = ('site','controller','valve','timestamp','text')
	list_filter = ('site','controller','valve')
	date_hierarchy = 'timestamp'
	ordering = ('-timestamp',)

admin.site.register(Site, SiteAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Controller, ControllerAdmin)
admin.site.register(Valve, ValveAdmin)
admin.site.register(EnvGroup, EnvGroupAdmin)
admin.site.register(Level, LevelAdmin)
admin.site.register(History, HistoryAdmin)
admin.site.register(EnvItem, EnvItemAdmin)
admin.site.register(DayRange, DayRangeAdmin)
admin.site.register(Day, DayAdmin)
admin.site.register(DayTime, DayTimeAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(GroupOverride, GroupOverrideAdmin)
admin.site.register(ValveOverride, ValveOverrideAdmin)
admin.site.register(GroupAdjust, GroupAdjustAdmin)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(RainMeter, RainMeterAdmin)
admin.site.register(TempMeter, TempMeterAdmin)
admin.site.register(WindMeter, WindMeterAdmin)
admin.site.register(SunMeter, SunMeterAdmin)
admin.site.register(UserForSite, UserForSiteAdmin)
admin.site.register(Log, LogAdmin)


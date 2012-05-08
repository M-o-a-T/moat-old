from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman.models import Site,Feed,Controller,Valve,History,Environment,EnvironmentEffect,Level,Day,DayTime,Group,GroupOverride,ValveOverride,GroupAdjust,Schedule,RainMeter,UserForGroup

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
	fields = (('name','var','location','feed'),('flow','area','shade','runoff'), ('time','level','priority','comment'),('max_level','start_level','stop_level'))

class HistoryInline(admin.TabularInline):
	model = History
	extra = 0

class EnvironmentInline(admin.TabularInline):
	model = Environment
	extra = 0

class EnvironmentEffectInline(admin.TabularInline):
	model = EnvironmentEffect
	extra = 0

class LevelInline(admin.TabularInline):
	model = Level
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

class ValveOverrideInline(admin.TabularInline):
	model = ValveOverride
	extra = 0

class GroupAdjustInline(admin.TabularInline):
	model = GroupAdjust
	extra = 0

class ScheduleInline(admin.TabularInline):
	model = Schedule
	extra = 0

class RainMeterInline(admin.TabularInline):
	model = RainMeter
	extra = 0

class UserForGroupInline(admin.TabularInline):
	model = UserForGroup
	extra = 0


class SiteAdmin(admin.ModelAdmin):
	list_display = ('name','host')
	inlines = [
		FeedInline,
		ControllerInline,
		GroupInline,
		HistoryInline,
	]

class FeedAdmin(admin.ModelAdmin):
	list_display = ('name','site','flow','var')
	inlines = [
		ValveInline,
	]

class ControllerAdmin(admin.ModelAdmin):
	list_display = ('name','site','location')
	inlines = [
		ValveInline,
	]

class ValveAdmin(admin.ModelAdmin):
	list_display = ('name','controller','var','comment','time','level','priority','list_groups','flow','area','stop_level','start_level','max_level')
	inlines = [
		ValveOverrideInline,
		LevelInline,
		ScheduleInline,
	]

class LevelAdmin(admin.ModelAdmin):
	list_display = ('valve','time','level','flow')
	date_hierarchy = 'time'

class HistoryAdmin(admin.ModelAdmin):
	list_display = ('time','rate','rain')
	date_hierarchy = 'time'

class EnvironmentAdmin(admin.ModelAdmin):
	list_display = ('time','temp','wind','sun')
	date_hierarchy = 'time'

class EnvironmentEffectAdmin(admin.ModelAdmin):
	list_display = ('factor','temp','wind','sun')

class DayAdmin(admin.ModelAdmin):
	list_display = ('name','list_daytimes')
	inlines = [
		DayTimeInline,
	]

class DayTimeAdmin(admin.ModelAdmin):
	list_display = ('day',)
	pass

class GroupAdmin(admin.ModelAdmin):
	list_display = ('name','site','list_valves','list_days')
	fields = ('name','site',('valves','days'), ('adj_sun','adj_rain','adj_wind','adj_temp'))
	inlines = [
		GroupOverrideInline,
		GroupAdjustInline,
	]

class GroupOverrideAdmin(admin.ModelAdmin):
	list_display = ('group','start','duration','allowed')
	date_hierarchy = 'start'

class ValveOverrideAdmin(admin.ModelAdmin):
	list_display = ('valve','start','duration','running')
	date_hierarchy = 'start'

class GroupAdjustAdmin(admin.ModelAdmin):
	list_display = ('group','start','factor')
	date_hierarchy = 'start'

class ScheduleAdmin(admin.ModelAdmin):
	list_display = ('valve','start','duration','seen','changed')
	date_hierarchy = 'start'

class RainMeterAdmin(admin.ModelAdmin):
	list_display = ('name','var')

class UserForGroupAdmin(admin.ModelAdmin):
	list_display = ('user','group')

admin.site.register(Site, SiteAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Controller, ControllerAdmin)
admin.site.register(Valve, ValveAdmin)
admin.site.register(Level, LevelAdmin)
admin.site.register(History, HistoryAdmin)
admin.site.register(Environment, EnvironmentAdmin)
admin.site.register(EnvironmentEffect, EnvironmentEffectAdmin)
admin.site.register(Day, DayAdmin)
admin.site.register(DayTime, DayTimeAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(GroupOverride, GroupOverrideAdmin)
admin.site.register(ValveOverride, ValveOverrideAdmin)
admin.site.register(GroupAdjust, GroupAdjustAdmin)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(RainMeter, RainMeterAdmin)
admin.site.register(UserForGroup, UserForGroupAdmin)


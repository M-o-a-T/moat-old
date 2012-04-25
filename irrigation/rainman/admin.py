from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman.models import Site,Feed,Controller,Valve,Evaporation,Level,Day,DayTime,Group,GroupOverride,ValveOverride,GroupAdjust,Schedule

# SiteInline
class FeedInline(admin.TabularInline):
	model = Feed
	extra = 0

class ControllerInline(admin.TabularInline):
	model = Controller
	extra = 0

class ValveInline(admin.TabularInline):
	model = Valve
	extra = 0

class EvaporationInline(admin.TabularInline):
	model = Evaporation
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


class SiteAdmin(admin.ModelAdmin):
	inlines = [
		FeedInline,
		ControllerInline,
		GroupInline,
		EvaporationInline,
	]

class FeedAdmin(admin.ModelAdmin):
	inlines = [
		ValveInline,
	]

class ControllerAdmin(admin.ModelAdmin):
	inlines = [
		ValveInline,
	]

class ValveAdmin(admin.ModelAdmin):
	inlines = [
		ValveOverrideInline,
		LevelInline,
		ScheduleInline,
	]

class LevelAdmin(admin.ModelAdmin):
	pass

class EvaporationAdmin(admin.ModelAdmin):
	pass

class DayAdmin(admin.ModelAdmin):
	inlines = [
		DayTimeInline,
	]

class DayTimeAdmin(admin.ModelAdmin):
	pass

class GroupAdmin(admin.ModelAdmin):
	inlines = [
		ValveInline,
		GroupOverrideInline,
		GroupAdjustInline,
	]

class GroupOverrideAdmin(admin.ModelAdmin):
	pass

class ValveOverrideAdmin(admin.ModelAdmin):
	pass

class GroupAdjustAdmin(admin.ModelAdmin):
	pass

class ScheduleAdmin(admin.ModelAdmin):
	pass

admin.site.register(Site, SiteAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Controller, ControllerAdmin)
admin.site.register(Valve, ValveAdmin)
admin.site.register(Level, LevelAdmin)
admin.site.register(Evaporation, EvaporationAdmin)
admin.site.register(Day, DayAdmin)
admin.site.register(DayTime, DayTimeAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(GroupOverride, GroupOverrideAdmin)
admin.site.register(ValveOverride, ValveOverrideAdmin)
admin.site.register(GroupAdjust, GroupAdjustAdmin)
admin.site.register(Schedule, ScheduleAdmin)


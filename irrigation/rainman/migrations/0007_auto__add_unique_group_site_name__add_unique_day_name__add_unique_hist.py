# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Group', fields ['site', 'name']
        db.create_unique('rainman_group', ['site_id', 'name'])

        # Adding unique constraint on 'Day', fields ['name']
        db.create_unique('rainman_day', ['name'])

        # Adding unique constraint on 'History', fields ['site', 'time']
        db.create_unique('rainman_history', ['site_id', 'time'])

        # Adding unique constraint on 'Environment', fields ['site', 'time']
        db.create_unique('rainman_environment', ['site_id', 'time'])

        # Adding unique constraint on 'ValveOverride', fields ['valve', 'name']
        db.create_unique('rainman_valveoverride', ['valve_id', 'name'])

        # Adding unique constraint on 'ValveOverride', fields ['start', 'valve']
        db.create_unique('rainman_valveoverride', ['start', 'valve_id'])

        # Adding unique constraint on 'GroupOverride', fields ['group', 'name']
        db.create_unique('rainman_groupoverride', ['group_id', 'name'])

        # Adding unique constraint on 'GroupOverride', fields ['start', 'group']
        db.create_unique('rainman_groupoverride', ['start', 'group_id'])

        # Adding unique constraint on 'Site', fields ['name']
        db.create_unique('rainman_site', ['name'])

        # Adding unique constraint on 'Controller', fields ['site', 'name']
        db.create_unique('rainman_controller', ['site_id', 'name'])

        # Adding field 'RainMeter.site'
        db.add_column('rainman_rainmeter', 'site', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='rain_meters', to=orm['rainman.Site']), keep_default=False)

        # Adding unique constraint on 'RainMeter', fields ['site', 'name']
        db.create_unique('rainman_rainmeter', ['site_id', 'name'])

        # Adding unique constraint on 'DayTime', fields ['day', 'descr']
        db.create_unique('rainman_daytime', ['day_id', 'descr'])

        # Adding unique constraint on 'Level', fields ['valve', 'time']
        db.create_unique('rainman_level', ['valve_id', 'time'])

        # Adding unique constraint on 'EnvironmentEffect', fields ['wind', 'site', 'temp', 'sun']
        db.create_unique('rainman_environmenteffect', ['wind', 'site_id', 'temp', 'sun'])

        # Adding unique constraint on 'Schedule', fields ['start', 'valve']
        db.create_unique('rainman_schedule', ['start', 'valve_id'])

        # Adding unique constraint on 'GroupAdjust', fields ['start', 'group']
        db.create_unique('rainman_groupadjust', ['start', 'group_id'])

        # Adding unique constraint on 'Feed', fields ['site', 'name']
        db.create_unique('rainman_feed', ['site_id', 'name'])

        # Adding unique constraint on 'Valve', fields ['controller', 'name']
        db.create_unique('rainman_valve', ['controller_id', 'name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Valve', fields ['controller', 'name']
        db.delete_unique('rainman_valve', ['controller_id', 'name'])

        # Removing unique constraint on 'Feed', fields ['site', 'name']
        db.delete_unique('rainman_feed', ['site_id', 'name'])

        # Removing unique constraint on 'GroupAdjust', fields ['start', 'group']
        db.delete_unique('rainman_groupadjust', ['start', 'group_id'])

        # Removing unique constraint on 'Schedule', fields ['start', 'valve']
        db.delete_unique('rainman_schedule', ['start', 'valve_id'])

        # Removing unique constraint on 'EnvironmentEffect', fields ['wind', 'site', 'temp', 'sun']
        db.delete_unique('rainman_environmenteffect', ['wind', 'site_id', 'temp', 'sun'])

        # Removing unique constraint on 'Level', fields ['valve', 'time']
        db.delete_unique('rainman_level', ['valve_id', 'time'])

        # Removing unique constraint on 'DayTime', fields ['day', 'descr']
        db.delete_unique('rainman_daytime', ['day_id', 'descr'])

        # Removing unique constraint on 'RainMeter', fields ['site', 'name']
        db.delete_unique('rainman_rainmeter', ['site_id', 'name'])

        # Removing unique constraint on 'Controller', fields ['site', 'name']
        db.delete_unique('rainman_controller', ['site_id', 'name'])

        # Removing unique constraint on 'Site', fields ['name']
        db.delete_unique('rainman_site', ['name'])

        # Removing unique constraint on 'GroupOverride', fields ['start', 'group']
        db.delete_unique('rainman_groupoverride', ['start', 'group_id'])

        # Removing unique constraint on 'GroupOverride', fields ['group', 'name']
        db.delete_unique('rainman_groupoverride', ['group_id', 'name'])

        # Removing unique constraint on 'ValveOverride', fields ['start', 'valve']
        db.delete_unique('rainman_valveoverride', ['start', 'valve_id'])

        # Removing unique constraint on 'ValveOverride', fields ['valve', 'name']
        db.delete_unique('rainman_valveoverride', ['valve_id', 'name'])

        # Removing unique constraint on 'Environment', fields ['site', 'time']
        db.delete_unique('rainman_environment', ['site_id', 'time'])

        # Removing unique constraint on 'History', fields ['site', 'time']
        db.delete_unique('rainman_history', ['site_id', 'time'])

        # Removing unique constraint on 'Day', fields ['name']
        db.delete_unique('rainman_day', ['name'])

        # Removing unique constraint on 'Group', fields ['site', 'name']
        db.delete_unique('rainman_group', ['site_id', 'name'])

        # Deleting field 'RainMeter.site'
        db.delete_column('rainman_rainmeter', 'site_id')


    models = {
        'rainman.controller': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'Controller'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_on': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'controllers'", 'to': "orm['rainman.Site']"})
        },
        'rainman.day': {
            'Meta': {'object_name': 'Day'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'rainman.daytime': {
            'Meta': {'unique_together': "(('day', 'descr'),)", 'object_name': 'DayTime'},
            'day': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'times'", 'to': "orm['rainman.Day']"}),
            'descr': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'rainman.environment': {
            'Meta': {'unique_together': "(('site', 'time'),)", 'object_name': 'Environment'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {}),
            'temp': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'wind': ('django.db.models.fields.FloatField', [], {})
        },
        'rainman.environmenteffect': {
            'Meta': {'unique_together': "(('site', 'temp', 'wind', 'sun'),)", 'object_name': 'EnvironmentEffect'},
            'factor': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environment_effects'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'temp': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'wind': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        },
        'rainman.feed': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'Feed'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'rainman.group': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'Group'},
            'days': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['rainman.Day']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': "orm['rainman.Site']"}),
            'valves': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'groups'", 'symmetrical': 'False', 'to': "orm['rainman.Valve']"})
        },
        'rainman.groupadjust': {
            'Meta': {'unique_together': "(('group', 'start'),)", 'object_name': 'GroupAdjust'},
            'factor': ('django.db.models.fields.FloatField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'adjusters'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.groupoverride': {
            'Meta': {'unique_together': "(('group', 'name'), ('group', 'start'))", 'object_name': 'GroupOverride'},
            'allowed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'duration': ('django.db.models.fields.TimeField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.history': {
            'Meta': {'unique_together': "(('site', 'time'),)", 'object_name': 'History'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rain': ('django.db.models.fields.FloatField', [], {}),
            'rate': ('django.db.models.fields.FloatField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'history'", 'to': "orm['rainman.Site']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.level': {
            'Meta': {'unique_together': "(('valve', 'time'),)", 'object_name': 'Level'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'levels'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.rainmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'RainMeter'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'rainman.schedule': {
            'Meta': {'unique_together': "(('valve', 'start'),)", 'object_name': 'Schedule'},
            'changed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'max_length': '1'}),
            'duration': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'max_length': '1'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'schedules'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.site': {
            'Meta': {'object_name': 'Site'},
            'host': ('django.db.models.fields.CharField', [], {'default': "'localhost'", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'rate': ('django.db.models.fields.FloatField', [], {'default': '2'})
        },
        'rainman.valve': {
            'Meta': {'unique_together': "(('controller', 'name'),)", 'object_name': 'Valve'},
            'area': ('django.db.models.fields.FloatField', [], {}),
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Controller']"}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Feed']"}),
            'flow': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'max_level': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'priority': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runoff': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'shade': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'start_level': ('django.db.models.fields.FloatField', [], {'default': '8'}),
            'stop_level': ('django.db.models.fields.FloatField', [], {'default': '3'}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'rainman.valveoverride': {
            'Meta': {'unique_together': "(('valve', 'name'), ('valve', 'start'))", 'object_name': 'ValveOverride'},
            'duration': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Valve']"})
        }
    }

    complete_apps = ['rainman']

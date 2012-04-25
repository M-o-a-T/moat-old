# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Valve.comment'
        db.add_column('rainman_valve', 'comment', self.gf('django.db.models.fields.CharField')(default='', max_length=200), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Valve.comment'
        db.delete_column('rainman_valve', 'comment')


    models = {
        'rainman.controller': {
            'Meta': {'object_name': 'Controller'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_on': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'controllers'", 'to': "orm['rainman.Site']"})
        },
        'rainman.day': {
            'Meta': {'object_name': 'Day'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'rainman.daytime': {
            'Meta': {'object_name': 'DayTime'},
            'day': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'times'", 'to': "orm['rainman.Day']"}),
            'descr': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'rainman.environment': {
            'Meta': {'object_name': 'Environment'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environment'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {}),
            'temp': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'wind': ('django.db.models.fields.FloatField', [], {})
        },
        'rainman.feed': {
            'Meta': {'object_name': 'Feed'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'rainman.group': {
            'Meta': {'object_name': 'Group'},
            'days': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['rainman.Day']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': "orm['rainman.Site']"}),
            'valves': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'groups'", 'symmetrical': 'False', 'to': "orm['rainman.Valve']"})
        },
        'rainman.groupadjust': {
            'Meta': {'object_name': 'GroupAdjust'},
            'factor': ('django.db.models.fields.FloatField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'adjusters'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.groupoverride': {
            'Meta': {'object_name': 'GroupOverride'},
            'allowed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'duration': ('django.db.models.fields.TimeField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.history': {
            'Meta': {'object_name': 'History'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rain': ('django.db.models.fields.FloatField', [], {}),
            'rate': ('django.db.models.fields.FloatField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'history'", 'to': "orm['rainman.Site']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.level': {
            'Meta': {'object_name': 'Level'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'levels'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.rainmeter': {
            'Meta': {'object_name': 'RainMeter'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'rainman.schedule': {
            'Meta': {'object_name': 'Schedule'},
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rate': ('django.db.models.fields.FloatField', [], {'default': '2'})
        },
        'rainman.valve': {
            'Meta': {'object_name': 'Valve'},
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
            'Meta': {'object_name': 'ValveOverride'},
            'duration': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Valve']"})
        }
    }

    complete_apps = ['rainman']

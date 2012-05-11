# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'TempMeter.controller'
        db.delete_column('rainman_tempmeter', 'controller_id')

        # Deleting field 'RainMeter.controller'
        db.delete_column('rainman_rainmeter', 'controller_id')

        # Deleting field 'WindMeter.controller'
        db.delete_column('rainman_windmeter', 'controller_id')

        # Deleting field 'SunMeter.controller'
        db.delete_column('rainman_sunmeter', 'controller_id')


    def backwards(self, orm):
        
        # User chose to not deal with backwards NULL issues for 'TempMeter.controller'
        raise RuntimeError("Cannot reverse this migration. 'TempMeter.controller' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'RainMeter.controller'
        raise RuntimeError("Cannot reverse this migration. 'RainMeter.controller' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'WindMeter.controller'
        raise RuntimeError("Cannot reverse this migration. 'WindMeter.controller' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'SunMeter.controller'
        raise RuntimeError("Cannot reverse this migration. 'SunMeter.controller' and its values cannot be restored.")


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'rainman.controller': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'Controller'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
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
        'rainman.environmenteffect': {
            'Meta': {'object_name': 'EnvironmentEffect'},
            'factor': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'param_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environment_effects'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'temp': ('django.db.models.fields.FloatField', [], {'default': '20', 'null': 'True', 'blank': 'True'}),
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
            'adj_rain': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_sun': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_temp': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_wind': ('django.db.models.fields.FloatField', [], {'default': '1'}),
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
            'off_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'on_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.history': {
            'Meta': {'unique_together': "(('site', 'time'),)", 'object_name': 'History'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rain': ('django.db.models.fields.FloatField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'history'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {}),
            'temp': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'wind': ('django.db.models.fields.FloatField', [], {})
        },
        'rainman.level': {
            'Meta': {'unique_together': "(('valve', 'time'),)", 'object_name': 'Level'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'levels'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.log': {
            'Meta': {'object_name': 'Log'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'logs'", 'null': 'True', 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['rainman.Site']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'logs'", 'null': 'True', 'to': "orm['rainman.Valve']"})
        },
        'rainman.paramgroup': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'ParamGroup'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'factor': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rain': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'param_groups'", 'to': "orm['rainman.Site']"})
        },
        'rainman.rainmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'RainMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
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
            '_rain_delay': ('django.db.models.fields.PositiveIntegerField', [], {'default': '300'}),
            'host': ('django.db.models.fields.CharField', [], {'default': "'localhost'", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '50005'}),
            'rate': ('django.db.models.fields.FloatField', [], {'default': '2'})
        },
        'rainman.sunmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'SunMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sun_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        },
        'rainman.tempmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'TempMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'temp_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        },
        'rainman.userforgroup': {
            'Meta': {'object_name': 'UserForGroup'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'rainman.valve': {
            'Meta': {'unique_together': "(('controller', 'name'),)", 'object_name': 'Valve'},
            'area': ('django.db.models.fields.FloatField', [], {}),
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Controller']"}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Feed']"}),
            'flow': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'max_level': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'param_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.ParamGroup']"}),
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
            'off_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'on_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.windmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'WindMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wind_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['rainman']

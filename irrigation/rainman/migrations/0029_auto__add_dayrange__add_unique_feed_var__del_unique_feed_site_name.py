# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Feed', fields ['site', 'name']
        db.delete_unique('rainman_feed', ['site_id', 'name'])

        # Adding model 'DayRange'
        db.create_table('rainman_dayrange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
        ))
        db.send_create_signal('rainman', ['DayRange'])

        # Adding M2M table for field days on 'DayRange'
        db.create_table('rainman_dayrange_days', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('dayrange', models.ForeignKey(orm['rainman.dayrange'], null=False)),
            ('day', models.ForeignKey(orm['rainman.day'], null=False))
        ))
        db.create_unique('rainman_dayrange_days', ['dayrange_id', 'day_id'])

        # Adding unique constraint on 'Feed', fields ['var']
        db.create_unique('rainman_feed', ['var'])

    def backwards(self, orm):
        # Removing unique constraint on 'Feed', fields ['var']
        db.delete_unique('rainman_feed', ['var'])

        # Deleting model 'DayRange'
        db.delete_table('rainman_dayrange')

        # Removing M2M table for field days on 'DayRange'
        db.delete_table('rainman_dayrange_days')

        # Adding unique constraint on 'Feed', fields ['site', 'name']
        db.create_unique('rainman_feed', ['site_id', 'name'])

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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
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
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'controllers'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'rainman.day': {
            'Meta': {'object_name': 'Day'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'rainman.dayrange': {
            'Meta': {'object_name': 'DayRange'},
            'days': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'ranges'", 'symmetrical': 'False', 'to': "orm['rainman.Day']"}),
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
            'param_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environment_effects'", 'to': "orm['rainman.ParamGroup']"}),
            'sun': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'temp': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'wind': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        },
        'rainman.feed': {
            'Meta': {'object_name': 'Feed'},
            'db_max_flow_wait': ('django.db.models.fields.PositiveIntegerField', [], {'default': '300', 'db_column': "'max_flow_wait'"}),
            'flow': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feed_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'rainman.group': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'Group'},
            'adj_rain': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_sun': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_temp': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'adj_wind': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'days': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['rainman.DayRange']", 'symmetrical': 'False'}),
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
            'start': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        'rainman.groupoverride': {
            'Meta': {'unique_together': "(('group', 'name'), ('group', 'start'))", 'object_name': 'GroupOverride'},
            'allowed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_duration': ('django.db.models.fields.PositiveIntegerField', [], {'db_column': "'duration'"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'off_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'on_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        'rainman.history': {
            'Meta': {'unique_together': "(('site', 'time'),)", 'object_name': 'History'},
            'feed': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rain': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'history'", 'to': "orm['rainman.Site']"}),
            'sun': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'temp': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'wind': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        },
        'rainman.level': {
            'Meta': {'unique_together': "(('valve', 'time'),)", 'object_name': 'Level'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'levels'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.log': {
            'Meta': {'object_name': 'Log'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'logs'", 'null': 'True', 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['rainman.Site']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 21, 0, 0)', 'db_index': 'True'}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'logs'", 'null': 'True', 'to': "orm['rainman.Valve']"})
        },
        'rainman.paramgroup': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'ParamGroup'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'factor': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rain': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'param_groups'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'rainman.rainmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'RainMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '10'})
        },
        'rainman.schedule': {
            'Meta': {'unique_together': "(('valve', 'start'),)", 'object_name': 'Schedule'},
            'changed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'max_length': '1'}),
            'db_duration': ('django.db.models.fields.PositiveIntegerField', [], {'db_column': "'duration'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'max_length': '1'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'schedules'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.site': {
            'Meta': {'object_name': 'Site'},
            'db_rain_delay': ('django.db.models.fields.PositiveIntegerField', [], {'default': '300', 'db_column': "'rain_delay'"}),
            'db_rate': ('django.db.models.fields.FloatField', [], {'default': '2', 'db_column': "'rate'"}),
            'host': ('django.db.models.fields.CharField', [], {'default': "'localhost'", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '50005'}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'})
        },
        'rainman.sunmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'SunMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sun_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '10'})
        },
        'rainman.tempmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'TempMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'temp_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '10'})
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
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'verbose': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'rainman.valveoverride': {
            'Meta': {'unique_together': "(('valve', 'name'), ('valve', 'start'))", 'object_name': 'ValveOverride'},
            'db_duration': ('django.db.models.fields.PositiveIntegerField', [], {'db_column': "'duration'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'off_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'on_level': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.windmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'WindMeter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wind_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '10'})
        }
    }

    complete_apps = ['rainman']
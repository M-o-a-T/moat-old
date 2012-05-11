# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'EnvironmentEffect', fields ['wind', 'site', 'temp', 'sun']
        db.delete_unique('rainman_environmenteffect', ['wind', 'site_id', 'temp', 'sun'])

        # Removing unique constraint on 'Environment', fields ['site', 'time']
        db.delete_unique('rainman_environment', ['site_id', 'time'])

        # Deleting model 'Environment'
        db.delete_table('rainman_environment')

        # Adding model 'TempMeter'
        db.create_table('rainman_tempmeter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='temp_meters', to=orm['rainman.Site'])),
            ('controller', self.gf('django.db.models.fields.related.ForeignKey')(related_name='temp_meters', to=orm['rainman.Controller'])),
            ('var', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('weight', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
        ))
        db.send_create_signal('rainman', ['TempMeter'])

        # Adding unique constraint on 'TempMeter', fields ['site', 'name']
        db.create_unique('rainman_tempmeter', ['site_id', 'name'])

        # Adding model 'ParamGroup'
        db.create_table('rainman_paramgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='param_groups', to=orm['rainman.Site'])),
            ('factor', self.gf('django.db.models.fields.FloatField')(default=1.0)),
            ('rain', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('rainman', ['ParamGroup'])

        # Adding unique constraint on 'ParamGroup', fields ['site', 'name']
        db.create_unique('rainman_paramgroup', ['site_id', 'name'])

        # Adding model 'WindMeter'
        db.create_table('rainman_windmeter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='wind_meters', to=orm['rainman.Site'])),
            ('controller', self.gf('django.db.models.fields.related.ForeignKey')(related_name='wind_meters', to=orm['rainman.Controller'])),
            ('var', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('weight', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
        ))
        db.send_create_signal('rainman', ['WindMeter'])

        # Adding unique constraint on 'WindMeter', fields ['site', 'name']
        db.create_unique('rainman_windmeter', ['site_id', 'name'])

        # Adding model 'SunMeter'
        db.create_table('rainman_sunmeter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sun_meters', to=orm['rainman.Site'])),
            ('controller', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sun_meters', to=orm['rainman.Controller'])),
            ('var', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('weight', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
        ))
        db.send_create_signal('rainman', ['SunMeter'])

        # Adding unique constraint on 'SunMeter', fields ['site', 'name']
        db.create_unique('rainman_sunmeter', ['site_id', 'name'])

        # Deleting field 'History.rate'
        db.delete_column('rainman_history', 'rate')

        # Adding field 'History.temp'
        db.add_column('rainman_history', 'temp', self.gf('django.db.models.fields.FloatField')(default=0), keep_default=False)

        # Adding field 'History.wind'
        db.add_column('rainman_history', 'wind', self.gf('django.db.models.fields.FloatField')(default=0), keep_default=False)

        # Adding field 'History.sun'
        db.add_column('rainman_history', 'sun', self.gf('django.db.models.fields.FloatField')(default=0), keep_default=False)

        # Deleting field 'RainMeter.flag_only'
        db.delete_column('rainman_rainmeter', 'flag_only')

        # Adding field 'RainMeter.weight'
        db.add_column('rainman_rainmeter', 'weight', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1), keep_default=False)

        # Deleting field 'EnvironmentEffect.site'
        db.delete_column('rainman_environmenteffect', 'site_id')

        # Adding field 'EnvironmentEffect.param_group'
        db.add_column('rainman_environmenteffect', 'param_group', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='environment_effects', to=orm['rainman.Site']), keep_default=False)

        # Adding field 'Valve.param_group'
        db.add_column('rainman_valve', 'param_group', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='valves', to=orm['rainman.ParamGroup']), keep_default=False)


    def backwards(self, orm):
        
        # Removing unique constraint on 'SunMeter', fields ['site', 'name']
        db.delete_unique('rainman_sunmeter', ['site_id', 'name'])

        # Removing unique constraint on 'WindMeter', fields ['site', 'name']
        db.delete_unique('rainman_windmeter', ['site_id', 'name'])

        # Removing unique constraint on 'ParamGroup', fields ['site', 'name']
        db.delete_unique('rainman_paramgroup', ['site_id', 'name'])

        # Removing unique constraint on 'TempMeter', fields ['site', 'name']
        db.delete_unique('rainman_tempmeter', ['site_id', 'name'])

        # Adding model 'Environment'
        db.create_table('rainman_environment', (
            ('temp', self.gf('django.db.models.fields.FloatField')()),
            ('sun', self.gf('django.db.models.fields.FloatField')()),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='environments', to=orm['rainman.Site'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('wind', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('rainman', ['Environment'])

        # Adding unique constraint on 'Environment', fields ['site', 'time']
        db.create_unique('rainman_environment', ['site_id', 'time'])

        # Deleting model 'TempMeter'
        db.delete_table('rainman_tempmeter')

        # Deleting model 'ParamGroup'
        db.delete_table('rainman_paramgroup')

        # Deleting model 'WindMeter'
        db.delete_table('rainman_windmeter')

        # Deleting model 'SunMeter'
        db.delete_table('rainman_sunmeter')

        # User chose to not deal with backwards NULL issues for 'History.rate'
        raise RuntimeError("Cannot reverse this migration. 'History.rate' and its values cannot be restored.")

        # Deleting field 'History.temp'
        db.delete_column('rainman_history', 'temp')

        # Deleting field 'History.wind'
        db.delete_column('rainman_history', 'wind')

        # Deleting field 'History.sun'
        db.delete_column('rainman_history', 'sun')

        # Adding field 'RainMeter.flag_only'
        db.add_column('rainman_rainmeter', 'flag_only', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Deleting field 'RainMeter.weight'
        db.delete_column('rainman_rainmeter', 'weight')

        # User chose to not deal with backwards NULL issues for 'EnvironmentEffect.site'
        raise RuntimeError("Cannot reverse this migration. 'EnvironmentEffect.site' and its values cannot be restored.")

        # Deleting field 'EnvironmentEffect.param_group'
        db.delete_column('rainman_environmenteffect', 'param_group_id')

        # Adding unique constraint on 'EnvironmentEffect', fields ['wind', 'site', 'temp', 'sun']
        db.create_unique('rainman_environmenteffect', ['wind', 'site_id', 'temp', 'sun'])

        # Deleting field 'Valve.param_group'
        db.delete_column('rainman_valve', 'param_group_id')


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
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'factor': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rain': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'param_groups'", 'to': "orm['rainman.Site']"})
        },
        'rainman.rainmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'RainMeter'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rain_meters'", 'to': "orm['rainman.Controller']"}),
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
            'rate': ('django.db.models.fields.FloatField', [], {'default': '2'})
        },
        'rainman.sunmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'SunMeter'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sun_meters'", 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sun_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        },
        'rainman.tempmeter': {
            'Meta': {'unique_together': "(('site', 'name'),)", 'object_name': 'TempMeter'},
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'temp_meters'", 'to': "orm['rainman.Controller']"}),
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
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
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
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wind_meters'", 'to': "orm['rainman.Controller']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wind_meters'", 'to': "orm['rainman.Site']"}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['rainman']

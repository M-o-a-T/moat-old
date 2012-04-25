# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Site'
        db.create_table('rainman_site', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('rate', self.gf('django.db.models.fields.FloatField')(default=2)),
        ))
        db.send_create_signal('rainman', ['Site'])

        # Adding model 'Feed'
        db.create_table('rainman_feed', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='feeds', to=orm['rainman.Site'])),
            ('flow', self.gf('django.db.models.fields.FloatField')(default=10)),
        ))
        db.send_create_signal('rainman', ['Feed'])

        # Adding model 'Controller'
        db.create_table('rainman_controller', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='controllers', to=orm['rainman.Site'])),
            ('max_on', self.gf('django.db.models.fields.IntegerField')(default=3)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('rainman', ['Controller'])

        # Adding model 'Valve'
        db.create_table('rainman_valve', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('feed', self.gf('django.db.models.fields.related.ForeignKey')(related_name='valves', to=orm['rainman.Feed'])),
            ('controller', self.gf('django.db.models.fields.related.ForeignKey')(related_name='valves', to=orm['rainman.Controller'])),
            ('var', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('flow', self.gf('django.db.models.fields.FloatField')()),
            ('area', self.gf('django.db.models.fields.FloatField')()),
            ('max_level', self.gf('django.db.models.fields.FloatField')(default=10)),
            ('min_level', self.gf('django.db.models.fields.FloatField')(default=3)),
            ('shade', self.gf('django.db.models.fields.FloatField')(default=1)),
            ('time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('level', self.gf('django.db.models.fields.FloatField')(default=0)),
        ))
        db.send_create_signal('rainman', ['Valve'])

        # Adding model 'Level'
        db.create_table('rainman_level', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('valve', self.gf('django.db.models.fields.related.ForeignKey')(related_name='levels', to=orm['rainman.Valve'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('level', self.gf('django.db.models.fields.FloatField')()),
            ('is_open', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('rainman', ['Level'])

        # Adding model 'Evaporation'
        db.create_table('rainman_evaporation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='evaporations', to=orm['rainman.Site'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('rate', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('rainman', ['Evaporation'])

        # Adding model 'Day'
        db.create_table('rainman_day', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('rainman', ['Day'])

        # Adding model 'DayTime'
        db.create_table('rainman_daytime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('descr', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('day', self.gf('django.db.models.fields.related.ForeignKey')(related_name='times', to=orm['rainman.Day'])),
        ))
        db.send_create_signal('rainman', ['DayTime'])

        # Adding model 'Group'
        db.create_table('rainman_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='groups', to=orm['rainman.Site'])),
        ))
        db.send_create_signal('rainman', ['Group'])

        # Adding M2M table for field valves on 'Group'
        db.create_table('rainman_group_valves', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['rainman.group'], null=False)),
            ('valve', models.ForeignKey(orm['rainman.valve'], null=False))
        ))
        db.create_unique('rainman_group_valves', ['group_id', 'valve_id'])

        # Adding M2M table for field days on 'Group'
        db.create_table('rainman_group_days', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['rainman.group'], null=False)),
            ('day', models.ForeignKey(orm['rainman.day'], null=False))
        ))
        db.create_unique('rainman_group_days', ['group_id', 'day_id'])

        # Adding model 'GroupOverride'
        db.create_table('rainman_groupoverride', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='overrides', to=orm['rainman.Group'])),
            ('allowed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('duration', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('rainman', ['GroupOverride'])

        # Adding model 'ValveOverride'
        db.create_table('rainman_valveoverride', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('valve', self.gf('django.db.models.fields.related.ForeignKey')(related_name='overrides', to=orm['rainman.Valve'])),
            ('running', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('duration', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('rainman', ['ValveOverride'])

        # Adding model 'GroupAdjust'
        db.create_table('rainman_groupadjust', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='adjusters', to=orm['rainman.Group'])),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('factor', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('rainman', ['GroupAdjust'])

        # Adding model 'Schedule'
        db.create_table('rainman_schedule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('valve', self.gf('django.db.models.fields.related.ForeignKey')(related_name='schedules', to=orm['rainman.Valve'])),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('duration', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('rainman', ['Schedule'])


    def backwards(self, orm):
        
        # Deleting model 'Site'
        db.delete_table('rainman_site')

        # Deleting model 'Feed'
        db.delete_table('rainman_feed')

        # Deleting model 'Controller'
        db.delete_table('rainman_controller')

        # Deleting model 'Valve'
        db.delete_table('rainman_valve')

        # Deleting model 'Level'
        db.delete_table('rainman_level')

        # Deleting model 'Evaporation'
        db.delete_table('rainman_evaporation')

        # Deleting model 'Day'
        db.delete_table('rainman_day')

        # Deleting model 'DayTime'
        db.delete_table('rainman_daytime')

        # Deleting model 'Group'
        db.delete_table('rainman_group')

        # Removing M2M table for field valves on 'Group'
        db.delete_table('rainman_group_valves')

        # Removing M2M table for field days on 'Group'
        db.delete_table('rainman_group_days')

        # Deleting model 'GroupOverride'
        db.delete_table('rainman_groupoverride')

        # Deleting model 'ValveOverride'
        db.delete_table('rainman_valveoverride')

        # Deleting model 'GroupAdjust'
        db.delete_table('rainman_groupadjust')

        # Deleting model 'Schedule'
        db.delete_table('rainman_schedule')


    models = {
        'rainman.controller': {
            'Meta': {'object_name': 'Controller'},
            'host': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
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
        'rainman.evaporation': {
            'Meta': {'object_name': 'Evaporation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rate': ('django.db.models.fields.FloatField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'evaporations'", 'to': "orm['rainman.Site']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.feed': {
            'Meta': {'object_name': 'Feed'},
            'flow': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': "orm['rainman.Site']"})
        },
        'rainman.group': {
            'Meta': {'object_name': 'Group'},
            'days': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['rainman.Day']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': "orm['rainman.Site']"}),
            'valves': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['rainman.Valve']", 'symmetrical': 'False'})
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
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'rainman.level': {
            'Meta': {'object_name': 'Level'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.FloatField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'levels'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.schedule': {
            'Meta': {'object_name': 'Schedule'},
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'schedules'", 'to': "orm['rainman.Valve']"})
        },
        'rainman.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rate': ('django.db.models.fields.FloatField', [], {'default': '2'})
        },
        'rainman.valve': {
            'Meta': {'object_name': 'Valve'},
            'area': ('django.db.models.fields.FloatField', [], {}),
            'controller': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Controller']"}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'valves'", 'to': "orm['rainman.Feed']"}),
            'flow': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'max_level': ('django.db.models.fields.FloatField', [], {'default': '10'}),
            'min_level': ('django.db.models.fields.FloatField', [], {'default': '3'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'shade': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'var': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'rainman.valveoverride': {
            'Meta': {'object_name': 'ValveOverride'},
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'valve': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'overrides'", 'to': "orm['rainman.Valve']"})
        }
    }

    complete_apps = ['rainman']

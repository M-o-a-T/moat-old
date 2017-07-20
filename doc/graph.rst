============
Logging data
============

You can log data from events to some database.

The back-end is fed via sqlmix.async because I am lazy; TODO. switch to
async sqlalchemy.

You need these tables:

	create database moat
	create table data_type(id int auto_increment, tag char(255), primary key(id));
	create table data_log(id int auto_increment, data_type int not null,
		value float(40,10), timestamp timestamp not null DEFAULT CURRENT_TIMESTAMP,
		primary key(id), foreign key(data_type) references data_type(id));
	create table data_sum(id int auto_increment, data_type int not null,
		start datetime not null, order int not null, value float(40,10),
		min_value float(40,10), max_value float(40,10),
		primary key(id), unique key(order, start), 
		foreign key(data_type) references data_type(id));

You need the ``graph`` module, these config entries:

	config:
		sql:
			data_logger:
				server:
					username: test
					password: test
					host: localhost
					database: moat
				prefix: data_

and the database tables in ``scropts/graph.sql``.

Data aggregation is configured in SQL, via ``moat ext graph set``.

Logging works by calling ``moat ext graph log`` which only writes raw data to
the database. Data aggregation is the done by layers; layer zero is
the most-detailed view of the data (e.g. a five-minute interval); each
subsequent view should be a multiple of the previous interval.

The logger deletes the raw entries as they're aggregated to layer zero.
A layer's entries in turn are deleted when the layer's hold time passes *and*
the data have all been aggregated into the next layer (assuming that there is
one). Layers may be filled partially.


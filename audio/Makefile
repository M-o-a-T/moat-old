#!/usr/bin/make -f
##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##

OPT=2
CFLAGS=-O$(OPT) -g -Wall $(shell pkg-config --cflags glib-2.0)
LDLIBS=$(shell pkg-config --libs glib-2.0) -lportaudio

all: reader writer

reader: reader.o flow.o flow_read.o common.o
writer: writer.o flow.o flow_write.o common.o

test:
	sh ../test/audio.sh
	@cmp -s ../test/expect/fs20rw ../test/real/fs20rw

reader.o: reader.c common.h flow.h
writer.o: writer.c common.h flow.h
flow.o: flow.c flow.h flow_internal.h
flow_read.o: flow_read.c flow.h flow_internal.h
flow_write.o: flow_read.c flow.h flow_internal.h

install: all
	install -m 755 reader $(DESTDIR)/usr/lib/homevent/reader
	install -m 755 writer $(DESTDIR)/usr/lib/homevent/writer

clean:
	@rm -f *.o reader

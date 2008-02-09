#!/usr/bin/make -f
##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
CFLAGS=-I. -I../params -I../common \
	 -O$(OPT) -g -Wall $(shell pkg-config --cflags glib-2.0)
LDLIBS=$(shell pkg-config --libs glib-2.0) -lportaudio

all: reader writer

test:
	sh ../../test/audio.sh
	@cmp -s ../../test/expect/fs20rw ../../test/real/fs20rw

reader: reader.o flow.o flow_read.o common.o
writer: writer.o flow.o flow_write.o common.o

common.o: common.c common.h ../common/flow.h
flow.o: flow.c flow_internal.h ../common/flow.h
reader.o: reader.c ../common/flow.h common.h def_enable.h \
  ../params/data.fs20.h ../params/data.none.h ../params/data.em.h
writer.o: writer.c ../common/flow.h common.h def_enable.h \
  ../params/data.fs20.h ../params/data.none.h ../params/data.em.h
flow_read.o: ../common/flow_read.c flow_internal.h ../common/flow.h
	$(CC) $(CFLAGS) -c -o $@ $<
flow_write.o: ../common/flow_write.c flow_internal.h ../common/flow.h
	$(CC) $(CFLAGS) -c -o $@ $<

install: all
	install -m 755 reader $(DESTDIR)/usr/lib/homevent/reader
	install -m 755 writer $(DESTDIR)/usr/lib/homevent/writer

clean:
	@rm -f *.o reader

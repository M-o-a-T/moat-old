
CFLAGS=-O2 -g -Wall $(shell pkg-config --cflags glib-2.0)
LDLIBS=$(shell pkg-config --libs glib-2.0)

all: reader writer

reader: reader.o flow.o flow_read.o 
writer: writer.o flow.o flow_write.o 

flow.o: flow.c flow.h flow_internal.h
flow_read.o: flow_read.c flow.h flow_internal.h

install: all
	install -m 755 reader $(DESTDIR)/usr/lib/homevent/reader

clean:
	@rm -f *.o reader

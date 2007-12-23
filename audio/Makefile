
CFLAGS=-O2 -g -Wall

all: reader

reader: reader.o flow.o flow_read.o 

flow.o: flow.c flow.h flow_internal.h
flow_read.o: flow_read.c flow.h flow_internal.h

install: all
	install -m 755 reader $(DESTDIR)/usr/lib/homevent/reader

clean:
	@rm -f *.o reader

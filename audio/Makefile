
CFLAGS=-O2 -g -Wall

all: reader

reader: reader.o flow_in.o

install: all
	install -m 755 reader $(DESTDIR)/usr/lib/homevent/reader

clean:
	@rm -f *.o reader

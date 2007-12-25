/*
 *  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License (included; see the file LICENSE)
 *  for more details.
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <wait.h>

#include <glib.h>

#include "flow.h"

static int rate = 32000;
static char *progname;
static int progress = 0;

__attribute__((noreturn)) 
void usage(int exitcode, FILE *out)
{
	fprintf(out,"Usage: %s\n", progname);
	fprintf(out,"  Parameters:\n");
	fprintf(out,"    rate NUM          -- samples/second; default: 32000\n");
	fprintf(out,"    progress          -- print something to stderr, once a second\n");
	fprintf(out,"  Actual work (needs to be last!):\n");
	fprintf(out,"    exec program args -- run this program, read from stdin\n");
	exit(exitcode);
}

static int set_rate(int argc, char *argv[])
{
	if (!argc) usage(2,stderr);
	rate = atoi(*argv);
	if(rate <= 8000) {
		fprintf(stderr,"rate must be at least 8000.\n");
		usage(2,stderr);
	}
	return 1;
}

static int set_progress(int argc, char *argv[])
{
	progress = 1;
	return 0;
}


/*************** exec some other program **********************/

void printer(unsigned char *buf, unsigned int len)
{
	while(len--)
		printf("%02X",*buf++);
	putchar('\n');
	fflush(stdout);
}

GMainLoop *mainloop;
GIOChannel *input;
FLOW *f;
int wfd;

int writer(void *unused, unsigned char *buf, unsigned int len)
{
	int res = write(wfd,buf,len);
	if (progress && (res > 0))  {
		progress += res;
		if(progress > rate) {
			fprintf(stderr,"x\r");
			fflush(stderr);
			progress = (progress-1)%rate +1;
		}
	}
	return res;
}

gboolean reader (GIOChannel *source, GIOCondition condition, gpointer data __attribute((unused)))
{
	GIOStatus res;
	gchar *str = NULL;
	gsize len = 0;
	gsize tpos = 0;
	GError *err = NULL;
	gchar *rp,*wp;
	gchar part;

	if(!(condition & G_IO_IN))
		goto out;
	
	res = g_io_channel_read_line(input, &str,&len,&tpos,&err);
	if (res != G_IO_STATUS_NORMAL) 
		goto out;

	if(!tpos || tpos & 1) {
		fprintf(stderr,"Line length is %d\n",len);
		goto sout;
	}

	rp = str;
	wp = str;
	part = 0;
	while(tpos--) {
		if(*rp >= '0' && *rp <= '9') {
			part |= *rp++ - '0';
		} else if(*rp >= 'a' && *rp <= 'f') {
			part |= *rp++ - 'a' + 10;
		} else if(*rp >= 'A' && *rp <= 'F') {
			part |= *rp++ - 'A' + 10;
		} else {
			fprintf(stderr,"Unknown hex char %c\n",*rp);
			goto sout;
		}
		if (tpos & 1) {
			part <<= 4;
		} else {
			*wp++ = part;
			part = 0;
		}
	}
	if(flow_write_buf(f, (unsigned char *)str,wp-str)) {
		perror("write buf");
		g_free(str);
		goto out;
	}
	
sout:
	g_free(str);
	if(!(condition & ~G_IO_IN))
		return 1;
out:
	g_main_loop_quit(mainloop);
	return 0;
}

gboolean timer(void *unused __attribute__((unused)))
{
	if(flow_write_idle(f)) {
		perror("write idle");
		g_main_loop_quit(mainloop);
		return 0;
	}
	return 1;
}

__attribute__((noreturn)) 
static int do_exec(int argc, char *argv[])
{
	GPid pid;
	GError *err = NULL;
	
	if (!argc) usage(2,stderr);

	if(!g_spawn_async_with_pipes(".",argv,NULL, G_SPAWN_SEARCH_PATH,
			NULL,NULL, &pid, &wfd,NULL,NULL, &err)) {
		fprintf(stderr,"Could not for: %d: %s\n", err->code,err->message);
		exit(4);
	}
	
	f = flow_setup(rate, 3,4,5,6,7);
	flow_writer(f,writer,NULL);
	mainloop = g_main_loop_new(NULL, 0);
	input = g_io_channel_unix_new(0);
	g_io_channel_set_encoding (input, NULL, NULL);
	g_io_add_watch(input, G_IO_IN|G_IO_ERR|G_IO_HUP, reader,NULL);
	g_timeout_add (50, timer,NULL);
	g_main_loop_run(mainloop);
	exit(0);
}

typedef int (*pcall)(int,char **);
struct {
	const char *what;
	pcall code;
} work[] = {

	{"rate", set_rate},
	{"progress", set_progress},
	{"exec", do_exec},
};

int main(int argc, char *argv[])
{
	progname = rindex(argv[0],'/');
	if (!progname) progname = argv[0];
	else progname++;

	if(argc <= 1) usage(0,stdout);
	argc--; argv++;

	while(argc > 0) {
		const char *what = argv[0];
		argc--; argv++;
		int len;
		pcall code = NULL;

		for(len=sizeof(work)/sizeof(*work)-1;len>=0;len--) {
			if(!strcmp(work[len].what,what)) {
				code=work[len].code;
				break;
			}
		}
		if(!code) {
			fprintf(stderr,"%s: unknown keyword\n",what);
			usage(2,stderr);
		}
		len = (*code)(argc,argv);
		argc -= len; argv += len;
	}
	fprintf(stderr,"no action given\n");
	usage(2,stderr);
}

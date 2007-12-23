/*
 *  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

#include "flow.h"

static int rate = 32000;
static char *progname;

__attribute__((noreturn)) 
void usage(int exitcode, FILE *out)
{
	fprintf(out,"Usage: %s\n", progname);
	fprintf(out,"  Parameters:\n");
	fprintf(out,"    rate NUM          -- samples/second; default: 32000\n");
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

/*************** exec some other program **********************/

void printer(void *unused __attribute__((unused)),
	unsigned char *buf, unsigned int len)
{
	while(len--)
		printf("%02X",*buf++);
	putchar('\n');
	fflush(stdout);
}

__attribute__((noreturn)) 
static int do_exec(int argc, char *argv[])
{
	int r[2];
	int pid, c, res;
	FLOW *f;
	FILE *ifd;

	if (!argc) usage(2,stderr);
	if(pipe(r) < 0) {
		perror("pipe");
		exit(1);
	}

	pid = fork();
	if(pid < 0) {
		perror("fork");
		exit(1);
	}
	if(pid == 0) {
		dup2(r[1],1);
		close(r[0]);
		close(r[1]);
		if(argv[argc] != NULL) {
			fprintf(stderr,"Uh..??? argv array not NULL terminated\n");
			_exit(3);
		}

		execvp(argv[0],argv);
		perror("Program not found!\n");
		_exit(4);
	}
	ifd = fdopen(r[0],"r");
	close(r[1]);
	
	f = flow_setup(rate, 3,4,5,6,7);
	flow_reader(f,printer,NULL);

	while((c = getc(ifd)) != EOF) {
		unsigned char cc = c;
		flow_read_buf(f,&cc,1);
	}
	flow_free(f);

	do {
		res = waitpid(pid,&c,0);
	} while(((res != -1) || (errno == EINTR)) && (res != pid));
	if(res == -1) {
		perror("exit");
		c=5<<8;
	}
	exit(c>>8);
	/* NOTREACHED */
}

typedef int (*pcall)(int,char **);
struct {
	const char *what;
	pcall code;
} work[] = {

	{"rate", set_rate},
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

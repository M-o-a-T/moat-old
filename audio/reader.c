/*
 *  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
#include <sys/time.h>

#include <portaudio.h>

#include "flow.h"
#include "common.h"

static int timestamp = 0;

static int log_min,log_max, log_len=0;

__attribute__((noreturn)) 
void
usage(int exitcode, FILE *out)
{
	fprintf(out,"Usage: %s\n", progname);
	fprintf(out,"  Parameters (must be given first):\n");
	fprintf(out,"    rate NUM            -- samples/second; default: 32000\n");
	fprintf(out,"    timestamp           -- print a timestamp before the data\n");
	fprintf(out,"    progress            -- print something to stderr, once a second\n");
	fprintf(out,"    log MIN MAX NUM     -- trace receiver signal\n");
	fprintf(out,"  Protocols (need at least one):\n");
	fprintf(out,"    fs20                -- switches; includes heating\n");
	fprintf(out,"    em                  -- environment sensors\n");
	fprintf(out,"  Actual work (only one; must be last!):\n");
	fprintf(out,"    exec program args…  -- run this program\n");
	fprintf(out,"                           must write data stream to stdout\n");
	fprintf(out,"    portaudio interface -- read from this sound input\n");
	fprintf(out,"    portaudio           -- list sound inputs\n");
	exit(exitcode);
}

static int
set_log(int argc, char *argv[])
{
	if (argc < 3) usage(2,stderr);
	log_min = atoi(argv[0]);
	log_max = atoi(argv[1]);
	log_len = atoi(argv[2]);
	return 3;
}

static int
set_timestamp(int argc, char *argv[])
{
	timestamp = 1;
	return 0;
}

/*************** exec some other program **********************/

void
printer(void *_flow,
	const unsigned char *buf, unsigned int len)
{
	FLOW *flow = _flow;
	if(timestamp) {
		struct timeval tv;
		gettimeofday(&tv,NULL);
		printf("t%ld.%06ld\n",tv.tv_sec,tv.tv_usec);
	}
	putchar(flow_id(flow));
	while(len--)
		printf("%02X",*buf++);
	putchar('\n');
	fflush(stdout);
	if (!f_log)
		f_log = flow;
}

void
do_flow_rw(FLOW *f, unsigned int *x)
{
	flow_setup_reader(f,6,x);
	flow_reader(f,printer,f);
}


static int
enable_fs20(int argc, char *argv[])
{
	unsigned int x[R_IDLE+1] = {
#include "timing.fs20.read.h"
	};
	flow_setup(x,8,P_EVEN,1,'f');
	return 0;
}


static int
enable_em(int argc, char *argv[])
{
	unsigned int x[R_IDLE+1] = {
#include "timing.em.read.h"
	};
	flow_setup(x,4,P_MARK,0,'e');
	return 0;
}


__attribute__((noreturn)) 
static int do_exec(int argc, char *argv[])
{
	int r[2];
	int pid, c, res;
	FILE *ifd;

	if(!f_log) usage(2,stderr);
	if(!argc) usage(2,stderr);

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
	
	if(log_len) flow_report(f_log,log_min,log_max,log_len);

	while((c = getc(ifd)) != EOF) {
		unsigned char cc = c;
		FLOW **f = flows;
		while(*f) flow_read_buf(*(f++),&cc,1);

		if(progress && progress++ == rate) {
			progress = 1;
			if(!flow_read_logging(f_log)) {
				fprintf(stderr,"x\r");
				fflush(stderr);
			}
		}
	}

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



/************************************************************************/

/* PortAudio. Note that
 * - ALSA does not work; use OSS inputs.
 * - Nonblocking mode does not work; this code blocks.
 */

static void do_pa_error(PaError err, const char *str)
{
	if(!err) return;
	fprintf(stderr,"PortAudio: %s: %s\n", str, Pa_GetErrorText(err));
	exit(2);
}

static int do_pa_callback(
    const void *input, void *output,
	unsigned long frameCount,
	const PaStreamCallbackTimeInfo* timeInfo,
	PaStreamCallbackFlags statusFlags,
	void *userData)
{
	static PaStreamCallbackFlags reported = 0;
	PaStreamCallbackFlags report = statusFlags & ~reported;
	FLOW *f = userData;

	if(report & paInputUnderflow) fprintf(stderr,"Input underflow\n");
	if(report & paInputOverflow) fprintf(stderr,"Input overflow\n");
	
	if(frameCount) {
		flow_read_buf(f,input,frameCount);
		if(progress) {
			progress += frameCount;
			if(progress > rate) {
				fprintf(stderr,"x\r");
				fflush(stderr);
				progress = (progress-1) % rate +1;
			}
		}
		if(0){
			const unsigned char *buf = input;
			while(frameCount--) fputc(*buf++,stdout);
			fflush(stdout);
		}
	} else
		fprintf(stderr,"empty buffer\n");

	reported = statusFlags;
	return paContinue;
}

__attribute__((noreturn)) 
static void do_pa_run(PaDeviceIndex idx, PaTime latency)
{
	PaError err;
	struct PaStreamParameters param;
	PaStream *stream = NULL;

	if(log_len) flow_report(f_log,log_min,log_max,log_len);

	memset(&param,0,sizeof(param));
	param.device = idx;
	param.channelCount = 1;
	param.sampleFormat = paUInt8;
	param.suggestedLatency = latency;

	err = Pa_IsFormatSupported(&param,NULL,rate);
	do_pa_error(err,"unsupported");

	err = Pa_OpenStream(&stream, &param, NULL, (double)rate,
	         paFramesPerBufferUnspecified,paNoFlag, /* &do_pa_callback */ NULL, NULL);
	do_pa_error(err,"open");
	
	err = Pa_StartStream(stream);
	do_pa_error(err,"start");

	while(1) {
#if 1
		unsigned char buf[128];
		FLOW **f = flows;
		err = Pa_ReadStream(stream,buf,sizeof(buf));
		if (err == paInputOverflowed)
			fprintf(stderr,"Input overflow\n");
		else do_pa_error(err, "read");
		while(*f)
			do_pa_callback(buf,NULL,sizeof(buf),NULL,0,*(f++));
#endif
		err = Pa_IsStreamActive(stream);
		if (err < 0) do_pa_error(err, "is_active");
		if (err == 0) break;
#if 0
		sleep(60);
#endif
	}
	err = Pa_AbortStream(stream);
	do_pa_error(err,"end");

	err = Pa_CloseStream(stream);
	do_pa_error(err,"close");

	err = Pa_Terminate();
	do_pa_error(err,"exit");
	exit(err != 0);
}

__attribute__((noreturn)) 
static int
do_portaudio(int argc, char *argv[])
{
	PaError err;
	PaDeviceIndex idx;

	err = Pa_Initialize();
	do_pa_error(err,"init");

	if(!f_log) usage(2,stderr);

	if (argc > 1) usage(2,stderr);
	idx = Pa_GetDeviceCount();
	if(!idx) {
		fprintf(stderr,"No devices available!\n");
		exit(1);
	} else if (idx < 0)
		do_pa_error(idx,"Device enum");

	while(idx-- > 0) {
		const struct PaDeviceInfo *dev = Pa_GetDeviceInfo(idx);
		if(argc) {
			if (!strcmp(dev->name,argv[0]))
				do_pa_run(idx, dev->defaultLowInputLatency);
		} else
			printf("%s (%f)\n",dev->name, dev->defaultSampleRate);
	}
	if (argc) {
		fprintf(stderr,"Device '%s' not found.\n",argv[0]);
		exit(1);
	}
	exit(0);
	/* NOTREACHED */
}


/************************************************************************/

/* Main code
 */

struct work work1[] = {
	{"rate", set_rate},
	{"progress", set_progress},
	{"timestamp", set_timestamp},
	{ NULL,NULL}
};
struct work work2[] = {
	{"fs20", enable_fs20},
	{"em", enable_em},
	{"log", set_log},
	{ NULL,NULL}
};
struct work work3[] = {
	{"exec", do_exec},
	{"portaudio", do_portaudio},
	{ NULL,NULL}
};

struct work *works[] = { work1, work2, work3, NULL };

int main(int argc, char *argv[])
{
	parse_args(argc,argv,works);
}

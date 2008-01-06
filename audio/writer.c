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
#include <time.h>
#include <sys/time.h>

#include <glib.h>
#include <portaudio.h>

#include "flow.h"
#include "common.h"

GMainLoop *mainloop;
GIOChannel *input;

int (*the_writer)(gchar *buf, guint len);

gchar *sendbuf;
guint sendbuf_len;
guint sendbuf_used;

gchar *fillbuf;
guint fillbuf_len;

guint bytes_sent;
struct timeval last_sent;
char blocking;

static int
write_idle()
{
	int n;
	struct timeval tn;

	if(sendbuf_used) {
		n = (*the_writer)(sendbuf, sendbuf_used);
		if (n == sendbuf_used) {
			sendbuf_used = 0;
			bytes_sent += n;
		} else if (n > 0) { /* partial write */
			sendbuf_used -= n;
			memcpy(sendbuf, sendbuf + n, sendbuf_used);

			/* Assume that the send buffer is full. Thus, there is no
			   point in keeping track of any accumulated backlog. */
			gettimeofday(&last_sent, NULL);
			bytes_sent = 0;
			return 0;
		} else if (n == 0) { /* EOF? */
			errno = 0;
			return -1;
		} else if ((errno == EINTR) || (errno == EAGAIN)) {
			return 0;
		} else {
			return -1;
		}
	}

	gettimeofday(&tn, NULL);

	/*
	 * Here we try to figure out whether to send zero fill-up bytes
	 * to keep the sound pipe's send buffer full.
	 */

	if (blocking) {
		/*
		 * No need to count anything if the interface is going to block
		 * on us anyway.
		 */
		n = rate/20;
		if (fillbuf_len < n) {
			free(fillbuf);
			fillbuf = malloc(n);
			if (!fillbuf) return -1;
			fillbuf_len = n;
			memset(fillbuf,0,n);
		}
		n = the_writer(fillbuf, n);
		if (n == 0) errno = 0;
		if (n <= 0) return -1;
		return 0;
	}
	/*
	 * First, clean up the byte counter..:
	 */
	if (bytes_sent > rate) {
		last_sent.tv_sec += bytes_sent/rate;
		bytes_sent %= rate;
	}
	if(timercmp(&last_sent, &tn, <)) {
		long long nb = (tn.tv_sec - last_sent.tv_sec) * 1000000 + (tn.tv_usec - last_sent.tv_usec);
		nb = (nb * rate) / 1000000 - bytes_sent;
		if (nb > 0) {
			if (nb < rate/5) { /* 1/5th second */
				n = nb;
				if (fillbuf_len < n) {
					free(fillbuf);
					fillbuf = malloc(n);
					if (!fillbuf) return -1;
					fillbuf_len = n;
					memset(fillbuf,0,n);
				}
				n = the_writer(fillbuf, n);
				if (n == 0) errno = 0;
				if (n <= 0) return -1;
				if (n == nb) {
					bytes_sent += n;
					return 0;
				}
				/* repeat, because the partial writeproc() could have
				 * taken up any amount of time */
				gettimeofday(&tn, NULL);
			}
			/* If we arrive here, either there was a buffer overrun or
			 * too much time has passed since the last call. Either way 
			 * we restart from now.
			 */
			last_sent = tn;
			bytes_sent = 0;
		}
	}
	return 0;
}

static void
bitwriter(void *unused, unsigned int hi, unsigned int lo)
{
	gchar *bp;
	guint req = hi+lo;
	if(sendbuf_len < sendbuf_used+req) {
		sendbuf_len += 100*req;
		sendbuf = realloc(sendbuf,sendbuf_len);
		if(!sendbuf) {
			perror("buffer malloc");
			exit(3);
		}
	}
	/* fprintf(stderr,"H%d L%d ",hi,lo); */
	bp = sendbuf+sendbuf_used;
	memset(bp,'\xFF',hi);
	memset(bp+hi,0,lo);
	sendbuf_used += req;

	if(!hi) write_idle();
	/* if(!hi) fputc('\n',stderr); */
}


static gboolean
reader (GIOChannel *source, GIOCondition condition, gpointer data __attribute((unused)))
{
	GIOStatus res;
	gchar *str = NULL;
	gsize len = 0;
	gsize tpos = 0;
	GError *err = NULL;
	gchar *rp,*wp;
	gchar part;
	char fid;
	FLOW **fp = flows;

	if(!(condition & G_IO_IN))
		goto out;
	
	res = g_io_channel_read_line(input, &str,&len,&tpos,&err);
	if (res != G_IO_STATUS_NORMAL) 
		goto out;

	if(tpos<2 || !(tpos & 1)) {
		fprintf(stderr,"Line length is %d\n",len);
		goto sout;
	}

	rp = str;
	wp = str;
	part = 0;

	fid = *rp++;
	while(--tpos) {
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
			*wp++ = part;
			part = 0;
		} else {
			part <<= 4;
		}
	}
	
	while(*fp) {
		if (flow_id(*fp) == fid) {
			if(flow_write_buf(*fp, (unsigned char *)str,wp-str)) {
				perror("write buf");
				g_free(str);
				goto out;
			}
			goto sout;
		}
		fp++;
	}
	fprintf(stderr,"ID '%c': unknown prefix; known: ",fid);
	for(fp = flows;*fp;fp++)
		fputc(flow_id(*fp),stderr);
	fputc('\n',stderr);
	goto out;
	
sout:
	g_free(str);
	if(!(condition & ~G_IO_IN))
		return 1;
out:
	g_main_loop_quit(mainloop);
	return 0;
}


__attribute__((noreturn)) 
void usage(int exitcode, FILE *out)
{
	fprintf(out,"Usage: %s\n", progname);
	fprintf(out,"  Parameters (must be given first):\n");
	fprintf(out,"    rate NUM            -- samples/second; default: 32000\n");
	fprintf(out,"    progress            -- print something to stderr, once a second\n");
	fprintf(out,"  Protocols (need at least one):\n");
	fprintf(out,"    fs20                -- switches; includes heating\n");
	fprintf(out,"    em                  -- environment sensors\n");
	fprintf(out,"  Actual work (only one; must be last!):\n");
	fprintf(out,"    exec program args…  -- run this program\n");
	fprintf(out,"                           must read data stream on stdin\n");
	fprintf(out,"    portaudio interface -- read from this sound input\n");
	fprintf(out,"    portaudio           -- list available inputs\n");
	fprintf(out,"                           best: use /dev/dsp* if available\n");
	exit(exitcode);
}


/*************** exec some other program **********************/

void printer(unsigned char *buf, unsigned int len)
{
	while(len--)
		printf("%02X",*buf++);
	putchar('\n');
	fflush(stdout);
}

int wfd;

static int
writer(gchar *buf, guint len)
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





static gboolean
timer(void *unused __attribute__((unused)))
{
	if(write_idle()) {
		perror("write idle");
		g_main_loop_quit(mainloop);
		return 0;
	}
	return 1;
}

static int
enable_fs20(int argc, char *argv[])
{
	unsigned int x[W_IDLE+1] = {
		[W_ZERO+W_MARK ] = 400,
		[W_ZERO+W_SPACE] = 400,
		[W_ONE +W_MARK ] = 600,
		[W_ONE +W_SPACE] = 600,
		[W_IDLE] = 2000,
	};
	flow_setup(x,8,P_EVEN,1,'f');
	return 0;
}

static int
enable_em(int argc, char *argv[])
{
	unsigned int x[W_IDLE+1] = {
		[W_ZERO+W_MARK ] = 855,
		[W_ZERO+W_SPACE] = 366,
		[W_ONE +W_MARK ] = 366,
		[W_ONE +W_SPACE] = 855,
		[W_IDLE] = 2000,
	};
	flow_setup(x,4,P_MARK,0,'e');
	return 0;
}

void
do_flow_rw(FLOW *f, unsigned int *x)
{
	flow_setup_writer(f,10,x);
	flow_writer(f,bitwriter,NULL);
}

__attribute__((noreturn)) 
static int
do_exec(int argc, char *argv[])
{
	GPid pid;
	GError *err = NULL;
	
	if(!f_log) usage(2,stderr);
	if(!argc) usage(2,stderr);

	if(!g_spawn_async_with_pipes(".",argv,NULL, G_SPAWN_SEARCH_PATH,
			NULL,NULL, &pid, &wfd,NULL,NULL, &err)) {
		fprintf(stderr,"Could not for: %d: %s\n", err->code,err->message);
		exit(4);
	}
	
	the_writer = writer; blocking = 0;
	mainloop = g_main_loop_new(NULL, 0);
	input = g_io_channel_unix_new(0);
	g_io_channel_set_encoding (input, NULL, NULL);
	g_io_add_watch(input, G_IO_IN|G_IO_ERR|G_IO_HUP, reader,NULL);
	g_timeout_add (50, timer,NULL);
	g_main_loop_run(mainloop);
	exit(0);
}


/************************************************************************/

/* PortAudio. Note that ALSA and non-blocking mode have not yet been
 * tested because the reader doesn't work with those either.
 */

void *stream;

static void
do_pa_error(PaError err, const char *str)
{
	if(!err) return;
	fprintf(stderr,"PortAudio: %s: %s\n", str, Pa_GetErrorText(err));
	exit(2);
}

int pa_chans;

int
pawriter(gchar *buf, guint len)
{
	PaError err;
	if(pa_chans > 1) {
		gchar *xbuf = alloca(len*pa_chans);
		gchar *xb = xbuf;
		gchar *b = buf;
		int i,j;
		for(i=len;i>0;i--,b++) 
			for (j=pa_chans;j>0;j++) 
				*xb++ = *b;
		buf=xbuf;
	}
	err = Pa_WriteStream(stream, buf,len);
	do_pa_error(err,"write");
	return len;
}

gboolean
idler(void *unused __attribute__((unused)))
{
	if(write_idle()) {
		perror("write idle");
		g_main_loop_quit(mainloop);
		return 0;
	}
	return 1;
}

__attribute__((noreturn)) 
static void
do_pa_run(PaDeviceIndex idx, PaTime latency)
{
	PaError err;
	struct PaStreamParameters param;
	PaStream *stream = NULL;

	memset(&param,0,sizeof(param));
	pa_chans = 1;
	param.device = idx;
	param.channelCount = 1;
	param.sampleFormat = paUInt8;
	param.suggestedLatency = latency;

	err = Pa_IsFormatSupported(NULL,&param,rate);
	if(err) {
		param.channelCount = 2;
		pa_chans = 2;
		err = Pa_IsFormatSupported(NULL,&param,rate);
		do_pa_error(err,"unsupported");
	}

	err = Pa_OpenStream(&stream, NULL, &param, (double)rate,
	         paFramesPerBufferUnspecified,paNoFlag, /* &do_pa_callback */ NULL, NULL);
	do_pa_error(err,"open");
	
	err = Pa_StartStream(stream);
	do_pa_error(err,"start");

	the_writer = pawriter; blocking = 1;

	mainloop = g_main_loop_new(NULL, 0);
	input = g_io_channel_unix_new(0);
	g_io_channel_set_encoding (input, NULL, NULL);
	g_io_add_watch(input, G_IO_IN|G_IO_ERR|G_IO_HUP, reader,NULL);
	g_idle_add (idler,NULL);
	g_main_loop_run(mainloop);

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

	if(!f_log) usage(2,stderr);
	if(argc > 1) usage(2,stderr);

	err = Pa_Initialize();
	do_pa_error(err,"init");

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
	{ NULL,NULL}
};
struct work work2[] = {
	{"fs20", enable_fs20},
	{"em", enable_em},
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

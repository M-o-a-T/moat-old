#include <stdio.h>

/**
 * Analyze incoming 868.35MHz signal.
 * Assumes 1-byte 1-channel values on stdin.
 * Sensible values for low/mid/high for 32kHz seem to be (8,14,26).
 */
void flow(int low, int mid, int high)
{
	int c;
	int len = 0;
	char hi;
	char lasthi;
	int cnt;
	int qsum;
	unsigned int nby = 0;

	unsigned char byt,bit;
	char syn;

	goto init;

	while((c=getchar()) != EOF) {
		if(!(++nby & 0x3FFF))  {
			fprintf(stderr,"%d\r",(nby >> 14)&7); /* bits above */
			fflush(stderr);
		}
		hi = ((c & 0x80) != 0);
		if(hi == lasthi) {
			cnt++;
			continue;
		}
		lasthi = hi;
		if (hi) {
			cnt = 0;
			continue;
		}
		if(cnt < low || cnt > high)
			goto init;
		hi = (cnt >= mid);
		cnt = 0;

		if (!syn) {
			++bit;
			if(!hi) continue;
			if(bit < 6) goto init;
			bit = 0;
			syn=1;
			continue;
		}
		if(++bit <= 8) {
			byt = (byt<<1) | hi;
			continue;
		}
		unsigned char par = byt ^ (byt >> 4);
		par ^= par >> 2;
		par ^= par >> 1;
		if((par&1) == !hi)
			goto init;
		if(++len > 50)
			goto init;
		printf("%02x",byt);
		bit=0;
		continue;

init:
		if(len) {
			putchar('\n'); fflush(stdout);
			len = 0;
		}
		byt = 0;
		bit = 0;
		cnt = 0;
		lasthi = 0;
		hi = 0;
		syn = 0;
		qsum = 0;
	}
}

int main(int argc,char *argv[]) {
	int rate = (argc>1)?atoi(argv[1]):32000;
#define r(x) (int)(rate*.0001*x)
	flow(r(3),r(5),r(7));
}

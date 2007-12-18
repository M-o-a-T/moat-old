#include <stdio.h>

/**
 * Analyze incoming 868.35MHz signal.
 * Assumes 1-byte 1-channel values on stdin.
 * Sensible values for low/mid/high for 32kHz seem to be (8,14,26).
 */
void flow(int low, int mid, int high)
{
	int c;
	unsigned char buf[20];
	unsigned char *bp = buf;
	char hi;
	char lasthi;
	int cnt;
	int qsum;
	int nby = 0;

	unsigned char byt,bit;
	char syn;

	goto init;

	while((c=getchar()) != EOF) {
		if(!(++nby % 10000))  {
			printf("%d\r",(nby/10000)%10);
			fflush(stdout);
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
		} else if(bit == 9) {
			unsigned char par = byt ^ (byt >> 4);
			par ^= par >> 2;
			par ^= par >> 1;
			if((par&1) == !hi) {
				printf("? PARITY\n");
				goto init;
			} else {
				int len=bp-buf;
				if(len == 4 + ((buf[3]&0x20) != 0)) {
					qsum -= byt;
					/*
					if(qsum & 0xFF) {
						printf("? SUM %x %x\n",qsum,byt);
						goto init;
					}
					*/
					{
						int i = 0;
						printf("%d",len);
						while(i < len) {
							printf(" %02x",buf[i++]);
						}
						printf(" %d\n",(-qsum)&0xFF);
						fflush(stdout);
					}
					goto init;
				}
				qsum += byt;
				*bp++ = byt;
				bit=0;
			}
		}

		continue;
init:
		bp = buf;
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

#include <stdio.h>

void dgram(int nlo,int nhi, int nbyt, unsigned char *byt)
{
#define R(x) \
	do { \
		int _i; \
		for(_i=0;_i<x;_i++) putchar('\xFF'); \
		for(_i=0;_i<x;_i++) putchar('\0'); \
	} while(0)
#define L() R(nlo)
#define H() R(nhi)
#define X(x) do { if((x)) H(); else L(); } while(0)
#define B(b) \
	do { \
		unsigned char _m = 0x80; \
		char _b = (b); \
		while(_m) { \
			X(_b & _m); \
			_m >>= 1; \
		} \
		_b ^= _b >> 4; \
		_b ^= _b >> 2; \
		_b ^= _b >> 1; \
		X(_b & 1); \
	} while(0) \

	int i;
	for(i=0;i<12;i++) L();
	H();
	while(nbyt--) { B(*byt); byt++; }
	L(); for(i=0;i<nhi*100;i++) putchar('\0');

	
}

int main(int argc, char *argv[]) {
	int rate = (argc>1)?atoi(argv[1]):32000;
#define r(x) (int)(rate*.0001*x)
	int i;

	while(1) { 
		dgram(r(4),r(6), 4,"\x8c\x8d\x13\x12\x44");
		fflush(stdout);
		exit(0);
	}

#if 0
	while(1) {
		for(i=0;i<r(4);i++)
			putchar('\0');
		for(i=0;i<r(4);i++)
			putchar('\377');
		for(i=0;i<r(6);i++)
			putchar('\0');
		for(i=0;i<r(6);i++)
			putchar('\377');
	}
#endif
}

#include <cstdint>
#include <cstdio>
#include <cstring>
#pragma pack(push,1)
struct Event {double t;uint32_t ip;uint8_t ttl;char q[48];};
#pragma pack(pop)
static_assert(sizeof(Event)==61, "Unexpected event record size");
int main(int argc,char**argv){
 if(argc!=3)return 2;FILE*in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");if(!in||!out)return 3;
 static char inbuf[1<<20],outbuf[1<<20];setvbuf(in,inbuf,_IOFBF,sizeof(inbuf));setvbuf(out,outbuf,_IOFBF,sizeof(outbuf));
 Event e;while(fread(&e,sizeof(e),1,in)==1){fprintf(out,"%.9f 100 %u.%u.%u.%u %u 1 %.*s\n",e.t+10000,e.ip>>24,(e.ip>>16)&255,(e.ip>>8)&255,e.ip&255,e.ttl,48,e.q);}
 fclose(in);fclose(out);return 0;
}

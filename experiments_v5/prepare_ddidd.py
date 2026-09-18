"""Copy official release and apply only documented measurement/portability patches."""
from pathlib import Path
import re, shutil, hashlib, difflib, json
base=Path(__file__).resolve().parent
src=base/'vendor/ddidd'; dst=base/'ddidd_adapter'; dst.mkdir(exist_ok=True)
patch=[]
for name in ['ddidd.cc','fq.cc','fq.hh','hcf.cc','hcf.hh','wild.cc','wild.hh','filter.cc','filter.hh','utils.h','utils.cc']:
    old=(src/name).read_text(); new=old
    # Const correctness of read-only address arguments for clang.
    new=new.replace('char* ip', 'const char* ip').replace('char* src', 'const char* src')
    # Zero otherwise uninitialized runtime rate/decay fields in training records.
    new=new.replace('record rec;', 'record rec{};')
    if name=='ddidd.cc':
        needle='    return 0;\n}\n\n\nvoid printHelp'
        assert needle in new
        new=new.replace(needle,'    return totaloutcome;\n}\n\n\nvoid printHelp')
        # Preserve main() initialization and original process()/deploy(); substitute only I/O.
        new=new.replace('  loadfiles(readfolder.c_str(), process, saveresolvers, "",','  readfiles(readfolder.c_str(), process, saveresolvers, "",')
    if name=='utils.cc':
        # Retain verbatim parsing/address/trim routines. Avoid Linux pcap/timezone transport.
        names=['trim','checkdigits','gettwo','parse','shouldprocess2']
        parts=['#include "utils.h"\n']
        for fn in names:
            m=re.search(r'^(?:string|bool|int) '+fn+r'\(',new,re.M); assert m,fn
            start=m.start(); a=new.index('{',m.end()); depth=1; b=a+1
            while depth:
                depth += (new[b]=='{')-(new[b]=='}'); b+=1
            parts.append(new[start:b]+'\n')
        new='\n'.join(parts)+r'''
// Event transport: optional forked replay shares only an identical benign prefix.
// Each child inherits the exact upstream runtime state and then sees one test.
static void replayfile(const string& file,const string& output,
 int (*process)(char*,double&,int&,int&)) {
 ifstream in(file); ofstream out(output,ios::binary);
 if(!in||!out){cerr<<"Cannot read/write events\n";exit(2);}
 string line;double t=0;int len=0,ttl=0;
 while(getline(in,line)){
  vector<char> data(line.begin(),line.end());data.push_back(0);
  int result=process(data.data(),t,len,ttl);out.put(result==2?1:0);
 }
}
void readfiles(const char* file, int (*process)(char*, double&, int&, int&),
 void (*savestats)(string), string, string, long int, int) {
 const char* output=getenv("DDIDD_DECISIONS");if(!output){cerr<<"Missing decisions path\n";exit(2);}
 replayfile(file,output,process);
 const char* batch=getenv("DDIDD_BATCH_FILE");if(!batch)return;
 ifstream cases(batch);string line;
 while(getline(cases,line)){
  istringstream row(line);string input,out,log;
  getline(row,input,'\t');getline(row,out,'\t');getline(row,log,'\t');
  cout.flush();cerr.flush();fflush(nullptr);
  pid_t pid=fork();if(pid<0)exit(3);
  if(pid==0){
   if(!freopen(log.c_str(),"w",stdout))exit(4);
   replayfile(input,out,process);cout.flush();fflush(nullptr);exit(0);
  }
  int status=0;if(waitpid(pid,&status,0)<0 || !WIFEXITED(status) || WEXITSTATUS(status)!=0)exit(5);
 }
}
'''
        new=new.replace('#include "utils.h"','#include "utils.h"\n#include <vector>\n#include <unistd.h>\n#include <sys/wait.h>',1)
    (dst/name).write_text(new)
    if old!=new: patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='upstream/'+name,tofile='adapter/'+name))
(dst/'upstream.patch').write_text(''.join(patch))
zone=base/'vendor/iana-tlds-20260913.txt'
assert zone.exists(),'The dated IANA TLD snapshot must accompany this release.'
(dst/'rootzone').write_text('\n'.join(x.lower() for x in zone.read_text().splitlines() if x and not x.startswith('#'))+'\n')
(base/'results/upstream_manifest.json').write_text(json.dumps({'url':'https://ant.isi.edu/software/ddidd/ddidd-0.1.tar.gz','sha256':hashlib.sha256((base/'vendor/ddidd-0.1.tar.gz').read_bytes()).hexdigest(),'patch':'ddidd_adapter/upstream.patch'},indent=2))

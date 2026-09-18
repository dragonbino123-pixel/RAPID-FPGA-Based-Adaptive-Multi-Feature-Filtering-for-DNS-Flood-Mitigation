"""Generate the published synthetic query workload without detector implementations."""
from pathlib import Path
from collections import Counter
import argparse, csv, hashlib, json, random
import numpy as np

B = Path(__file__).resolve().parent
DATA = B / 'data'
TRAIN = 300
TEST = 30
LEGIT = 50000
CAPACITY = 100000
SEEDS = list(range(20260611, 20260616))
ATTACKS = ['fixed_qname_flood', 'random_subdomain_flood', 'spoofed_source_flood',
           'compromised_resolver_burst', 'ttl_consistent_evasion', 'low_rate_distributed', 'adaptive_mixed']
CONTROLS = ['stable_known', 'resolver_churn', 'name_churn', 'route_change', 'legitimate_surge']
SCENARIOS = ATTACKS + CONTROLS
DT = np.dtype([('t', 'f8'), ('src', 'u4'), ('ttl', 'u1'), ('q', 'S48'), ('attack', '?')])
DTI = np.dtype([('t', 'f8'), ('src', 'u4'), ('ttl', 'u1'), ('q', 'S48')])
PREFIXES = np.array(['www', 'api', 'cdn', 'mail', 'auth', 'ns', 'login'])
PREFIX_WEIGHTS = np.array([.60, .15, .10, .06, .04, .02, .03])
DOMAIN_WEIGHTS = np.arange(1, 181, dtype=float) ** -1.1
DOMAIN_WEIGHTS /= DOMAIN_WEIGHTS.sum()
def ipstr(ip):return '.'.join(str((int(ip)>>k)&255) for k in (24,16,8,0))

def pop(seed):
 r=random.Random(seed);ips=np.arange(0x0a000001,0x0a000001+320,dtype='u4')
 ttls=np.array([r.choice([43,44,49,50,51,55,56,57]) for _ in ips],dtype='u1')
 domains=np.array([f'www{i}.{r.choice(["com","net","org","edu"])}' for i in range(180)])
 weights=np.array([10+i%17 if i<160 else 1 for i in range(320)],dtype=float);weights/=weights.sum()
 return ips,ttls,domains,weights

def normal(rng,start,n,p,training=False,stable=False):
 # Marked Poisson process at the inspected service ingress. Fixed source-path
 # TTLs; the smooth demand intensity is continuous across t=0.
 ips,ttls,domains,weights=p;e=np.zeros(n,dtype=DT)
 e['t']=start+rng.random(n);ix=rng.choice(320,n,p=weights);e['src']=ips[ix]
 e['ttl']=ttls[ix]
 prefixes=rng.choice(PREFIXES,n,p=PREFIX_WEIGHTS)
 e['q']=np.char.add(np.char.add(prefixes,'.'),rng.choice(domains,n,p=DOMAIN_WEIGHTS))
 return e[np.argsort(e['t'],kind='stable')]

def intensity(t):
 return LEGIT*(1+.10*np.sin(2*np.pi*t/120))

def attack(rng,sec,kind,p):
 ips,ttls,domains,weights=p;n=90000 if kind=='ttl_consistent_evasion' else (168000 if kind=='adaptive_mixed' else 200000)
 e=np.zeros(n,dtype=DT);e['t']=sec+rng.random(n);e['attack']=True
 ix=rng.integers(0,320,n);e['src']=ips[ix];e['ttl']=ttls[ix]
 def fresh(sel):
  # A fresh source per attack query, as in the original logical generator.
  e['src'][sel]=0xac200001+sec*200000+np.arange(n,dtype='u4')[sel]
  e['ttl'][sel]=rng.choice([43,44,49,50,55,56],int(sel.sum()))
 def randomq(sel,bits=48,suffix=None):
  k=int(sel.sum());left=np.array([f'{int(v):0{(bits+3)//4}x}' for v in rng.integers(0,2**bits,k)])
  right=rng.choice(['com','net','org','edu'],k) if suffix is None else np.full(k,suffix)
  e['q'][sel]=np.char.add(np.char.add(left,'.'),right)
 allq=np.ones(n,dtype=bool)
 if kind=='fixed_qname_flood':
  fresh(np.arange(n)%5==0);e['q']=rng.choice(['www.target-zone.invalid','ns.target-zone.invalid','api.target-zone.invalid'],n)
 elif kind=='random_subdomain_flood':fresh(np.arange(n)%4==0);randomq(allq,suffix='victim-zone.invalid')
 elif kind=='spoofed_source_flood':
  new=np.arange(n)%3!=0;fresh(new);e['ttl'][~new]=ttls[ix[~new]]+rng.choice([8,16,24],int((~new).sum()));randomq(allq,40)
 elif kind=='compromised_resolver_burst':
  ix=np.arange(n)%18;e['src']=ips[ix];e['ttl']=ttls[ix];randomq(allq)
 elif kind=='ttl_consistent_evasion':
  ix=rng.integers(160,320,n);e['src']=ips[ix];e['ttl']=ttls[ix];randomq(allq)
 elif kind=='low_rate_distributed':fresh(allq);randomq(allq,52)
 elif kind=='adaptive_mixed':
  # Exactly 40k queries/s in each of four modes, 8k in the fifth.
  modes=np.repeat(np.arange(5),[40000,40000,40000,40000,8000]);rng.shuffle(modes)
  m=modes==0;e['q'][m]='www.hybrid-zone.invalid'
  m=modes==1;fresh(m);randomq(m,suffix='com')
  m=modes==2;e['ttl'][m]+=16;randomq(m,suffix='net')
  m=modes==3;ix3=rng.integers(0,18,int(m.sum()));e['src'][m]=ips[ix3];e['ttl'][m]=ttls[ix3];randomq(m)
  randomq(modes==4)
 else:raise ValueError(kind)
 return e

def make_training(seed):
 rng=np.random.default_rng(np.random.SeedSequence([seed,500]));p=pop(seed)
 return np.concatenate([normal(rng,s,int(rng.poisson(intensity(s+.5))),p,True) for s in range(-TRAIN,0)])

def make_legitimate(seed):
 p=pop(seed);rng=np.random.default_rng(np.random.SeedSequence([seed,501]))
 return np.concatenate([normal(rng,s,int(rng.poisson(intensity(s+.5))),p) for s in range(TEST)])

def make_test(seed,scenario):
 p=pop(seed);legit=make_legitimate(seed)
 rng=np.random.default_rng(np.random.SeedSequence([seed,502,SCENARIOS.index(scenario)]))
 # Novelty and route changes are separately identified conditions. Never
 # silently insert them into the ordinary attack-comparison background.
 if scenario=='resolver_churn':
  ix=rng.choice(len(legit),round(.012*len(legit)),replace=False)
  k=rng.integers(0,4,len(ix));legit['src'][ix]=0xac100001+k
  legit['ttl'][ix]=np.array([44,49,50,55],dtype='u1')[k]
 elif scenario=='name_churn':
  ix=rng.choice(len(legit),round(.01*len(legit)),replace=False)
  legit['q'][ix]=np.array(['fresh.'+q.decode().split('.',1)[1] for q in legit['q'][ix]])
 elif scenario=='route_change':
  # One previously learned resolver changes route once, halfway through test.
  ix=(legit['src']==p[0][100])&(legit['t']>=TEST/2)
  legit['ttl'][ix]+=1
 elif scenario=='legitimate_surge':
  # An independent 50% demand rise with the same source/name/path model.
  extra=np.concatenate([normal(rng,s,int(rng.poisson(.5*intensity(s+.5))),p) for s in range(TEST)])
  legit=np.concatenate([legit,extra])
 chunks=[legit]
 if scenario in ATTACKS:
  arng=np.random.default_rng(np.random.SeedSequence([seed,503,ATTACKS.index(scenario)]))
  chunks += [attack(arng,s,scenario,p) for s in range(TEST)]
 e=np.concatenate(chunks);return e[np.argsort(e['t'],kind='stable')]

def binary(e,path):
 e[['t','src','ttl','q']].astype(DTI).tofile(path)

def benign_audit(e,seed,ordinary=True):
 l=e[~e['attack']];p=pop(seed)
 assert np.all(np.diff(e['t'])>=0)
 if ordinary:
  ix=l['src'].astype('i8')-int(p[0][0])
  assert np.all((ix>=0)&(ix<320))
  assert np.array_equal(l['ttl'],p[1][ix])
 vocabulary=set((pre+'.'+str(dom)).encode() for pre in PREFIXES for dom in p[2])
 q,c=np.unique(l['q'],return_counts=True)
 unseen=sum(int(n) for one,n in zip(q,c) if one not in vocabulary)
 if ordinary:assert unseen==0
 return dict(legitimate_queries=len(l),legitimate_sha256=hashlib.sha256(l.tobytes()).hexdigest(),
             ordinary_source_paths_fixed=ordinary,unseen_catalogue_queries=unseen,
             counts_per_second=np.unique(np.floor(l['t']).astype(int),return_counts=True)[1].tolist())

def trainfiles(e,d):
 unique,counts=np.unique(e['q'],return_counts=True);tld=Counter();stld=Counter();full=Counter()
 for q,n in zip(unique,counts):
  q=q.decode();parts=q.split('.');full[q]=int(n);tld[parts[-1]]+=int(n);stld['.'.join(parts[-2:])]+=int(n)
 with (d/'fq.train').open('w') as f:
  for tag,c in [('TLD',tld),('sTLD',stld),('Full',full)]:
   f.writelines(f'{tag} {q} x {v}\n' for q,v in sorted(c.items()))
 pairs=np.unique(e[['src','ttl']]);(d/'hcf.train').write_text('\n'.join(f'{ipstr(x["src"])} {x["ttl"]}' for x in pairs)+'\n')
 ix=(e['src'].astype('i8')-0x0a000001)*TRAIN+np.floor(e['t']+TRAIN).astype('i8')
 hist=np.bincount(ix,minlength=320*TRAIN).reshape(320,TRAIN)
 with (d/'wr.train').open('w') as f:
  for i,one in enumerate(hist):
   cumulative=np.r_[0,np.cumsum(one)];stats=[]
   for w in [1,2,4,8,16,32,64,128,256]:
    v=cumulative[w:]-cumulative[:-w];stats.extend([f'{v.mean():.12g}',f'{v.var():.12g}',str(len(v))])
   f.write(ipstr(0x0a000001+i)+' '+' '.join(stats)+'\n')

def metrics(e,drop):
 a=e['attack'];l=~a;na=int(a.sum());nl=int(l.sum());ad=int((a&drop).sum());ld=int((l&drop).sum())
 return dict(attack_count=na,legitimate_count=nl,attack_dropped=ad,legitimate_dropped=ld,afr=100*ad/na if na else None,fpr=100*ld/nl,residual_attack_qps=(na-ad)/TEST,forwarded_qps=int((~drop).sum())/TEST)

def writecsv(path,rows):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def save_events(events, folder, stem):
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / (stem + '.npz'), events=events)
    binary(events, folder / (stem + '.bin'))
    return {'event_count': len(events), 'event_sha256': hashlib.sha256(events.tobytes()).hexdigest()}

def generate_training(seed, root):
    folder = root / str(seed)
    events = make_training(seed)
    manifest = save_events(events, folder, 'training')
    trainfiles(events, folder)
    manifest.update(seed=seed, seconds=TRAIN, training_count=len(events), audit=benign_audit(events, seed))
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Training generated:', seed, len(events), flush=True)

def generate_case(seed, scenario, root):
    events = make_test(seed, scenario)
    folder = root / str(seed) / scenario
    manifest = save_events(events, folder, 'events')
    audit = benign_audit(events, seed, scenario not in ['resolver_churn', 'name_churn', 'route_change'])
    if scenario in ATTACKS:
        assert audit['legitimate_sha256'] == hashlib.sha256(make_legitimate(seed).tobytes()).hexdigest()
    manifest.update(seed=seed, scenario=scenario, seconds=TEST, audit=audit)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Case generated:', seed, scenario, len(events), flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, nargs='+', default=SEEDS)
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=SCENARIOS)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--skip-training', action='store_true')
    mode.add_argument('--training-only', action='store_true')
    args = parser.parse_args()
    for seed in args.seeds:
        if not args.skip_training:
            generate_training(seed, args.data_dir)
        if not args.training_only:
            for scenario in args.scenarios:
                generate_case(seed, scenario, args.data_dir)

if __name__ == '__main__':
    main()

# Pull the numbers used in the paper out of the version-3 result files.
import json
from data2 import *
from model2 import capex
R=json.load(open('results3.json')); pl, bs=R['plan'], R['base']
Y=[str(t) for t in PLAN]
pi={w:SCEN[w]['p'] for w in SCEN}
def ehep(r): return {t: sum(pi[w]*r['hep_scen'][w][t] for w in SCEN) for t in Y}
out={}
out['obj']={k:(R[k]['obj'] if R.get(k) else None) for k in R if isinstance(R.get(k),dict) and 'obj' in R[k]}
out['spend_total']={k:sum(R[k]['spend'].values()) for k in R if isinstance(R.get(k),dict) and 'spend' in R[k]}
out['bs']={k:R[k].get('bs') for k in R if isinstance(R.get(k),dict) and 'bs' in R[k]}
out['hep_plan']=ehep(pl); out['hep_base']=ehep(bs); out['hep_ev']=ehep(R['EEV'])
# builds by project and period, public cost
agg={}
for k,v in pl['x'].items():
    p,n,t=k.split('|'); t=int(t)
    agg.setdefault(p,{}).setdefault(t,0); agg[p][t]+=v
per={'2027-29':range(2027,2030),'2030-32':range(2030,2033),'2033-36':range(2033,2037)}
tab={}
for p,d in agg.items():
    tab[p]={'units':sum(d.values()),'unit':P[p]['unit'],
            'pub':{k:sum(P[p]['pub']*capex(p,t)*d.get(t,0) for t in r) for k,r in per.items()},
            'tot':{k:sum(capex(p,t)*d.get(t,0) for t in r) for k,r in per.items()},
            'years':sorted(t for t,v in d.items() if v>1e-3)}
out['builds']=tab; out['circ']=pl['circ']; out['spend_year']=pl['spend']
# line cost
out['line_pub']=sum(LINE_COST*LINKS[k.split('|')[0]][3]*v for k,v in pl['circ'].items())
# regional winter evening cuts GWh
for name,r in (('plan',pl),('base',bs)):
    out['cuts_'+name]={n:{t:1000*r['UeW_PK_node'][n][t] for t in ('2028','2032','2036')} for n in NODES}
out['gen_plan']={k:{t:v[t] for t in ('2027','2036')} for k,v in pl['gen'].items()}
out['imp']={'plan':sum(pl['imp'][t] for t in Y),'base':sum(bs['imp'][t] for t in Y)}
out['Ue_share']={t: pl['Ue'][t] for t in Y}
out['dKG']=pl['dKG']; out['dUZ']=pl['dUZ']; out['Ugi']={'plan':pl['Ugi'],'base':bs['Ugi']}; out['Ug']={'plan':pl['Ug'],'base':bs['Ug']}
out['pg']={t:pl['pg'][t] for t in ('2027','2036')}
out['sens']=json.load(open('sens3.json')); out['extra']=json.load(open('extra3.json'))
out['evcheck']=json.load(open('evcheck3.json')); out['frontier']=json.load(open('frontier3.json'))
out['barterval']=json.load(open('barterval.json'))
out['WS']=R['WS']; out['cv']=R.get('plan_cvar90')
json.dump(out, open('paper_numbers.json','w'), indent=1, default=float)
print('ok')

import json, pyomo.environ as pe, model2
from model2 import *
v=pe.value
REL=[(2027,2029,0.025),(2030,2036,0.002)]; CAPS=[(2030,1.5),(2032,1.0)]
def run(name, eps, eens, gi, fixzero=False):
    g0=model2.VOLL_GI; h0=model2.VOLL_G; model2.VOLL_GI=gi; model2.VOLL_G=max(h0, 2*gi)
    m=build(np2025=29.97, eens=eens, eps=eps, barter=not fixzero)
    if fixzero:
        for k in m.x: m.x[k].fix(0)
        for k in m.circ: m.circ[k].fix(0)
        m.yK.fix(0)
    r=solve(m, tl=900, gap=0.005); model2.VOLL_GI=g0; model2.VOLL_G=h0
    if r.best_feasible_objective is None: print(name,'INFEASIBLE'); return None
    hep={t:sum(m._pi[w]*v(m.HEP[t,w]) for w in m._S) for t in PLAN}
    spend={t:v(m.pubcash[t]) for t in PLAN}
    tot={p: round(sum(v(m.x[p,n,t]) for n in pnodes(p) for t in PLAN),1) for p in P}
    ugi={t:sum(m._pi[w]*v(m.Ugi[t,s,w]) for s in SEASONS for w in m._S) for t in PLAN}
    ue={t:sum(m._pi[w]*v(m.U[n,t,s,h,w]) for n in NODES for s in SEASONS for h in BLOCKS for w in m._S) for t in PLAN}
    d=dict(obj=v(m.obj), spend=spend, hep=hep, builds={k:x for k,x in tot.items() if x>0}, circ={str(k):v(m.circ[k]) for k in m.circ if v(m.circ[k])>0.5}, yK=v(m.yK), bs=v(m.bs), ugi=ugi, ue=ue)
    print(name,'spend',round(sum(spend.values())),'obj',round(d['obj']),'yK',round(d['yK']),'bs',round(d['bs'],2),d['builds'],d['circ'])
    print('  HEP',{t:round(x,2) for t,x in hep.items()})
    print('  industry gas cuts bcm',{t:round(x,2) for t,x in ugi.items()})
    print('  unserved TWh',{t:round(x,2) for t,x in ue.items()})
    return d
out={}
out['strict']=run('strict', CAPS, REL, 1000.0)
out['base_same_valuation']=run('nonew', None, None, 1000.0, fixzero=True)
json.dump(out, open('strict3.json','w'), indent=1, default=float)

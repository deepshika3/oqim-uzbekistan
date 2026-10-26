import json, copy, pyomo.environ as pe
import model2, data2
from model2 import *
NP=29.97; EPS=(2030,1.5); out={}
def go(name, **kw):
    m=build(np2025=NP, eps=EPS, **kw); r=solve(m, tl=900, gap=0.005)
    if r.best_feasible_objective is None: out[name]=None; print(name,'INFEASIBLE'); return
    tot={p: round(sum(pe.value(m.x[p,n,t]) for n in pnodes(p) for t in PLAN),1) for p in P}
    out[name]=dict(obj=pe.value(m.obj), spend=sum(pe.value(m.pubcash[t]) for t in PLAN), yK=pe.value(m.yK), builds=tot,
                   circ=sum(pe.value(m.circ[k]) for k in m.circ))
    print(name, round(out[name]['obj']), round(out[name]['spend']), 'K', round(out[name]['yK']), {k:v for k,v in tot.items() if v>0})
# probability of low gas path 0.7
go('lowgas_p70', prob=lambda sc: (0.5)*(0.7 if sc['sup']=='LOW' else 0.3)*WINTER[sc['w']])
# availability -5 points
AV0=copy.deepcopy(data2.AV)
for k in model2.AV:
    for s_ in model2.AV[k]: model2.AV[k][s_]-=0.05
go('avail_minus5')
for k in model2.AV:
    for s_ in model2.AV[k]: model2.AV[k][s_]=AV0[k][s_]
# links -25%
L0=dict(model2.LINKS)
for l in model2.LINKS: a,b,c,d=L0[l]; model2.LINKS[l]=(a,b,0.75*c,d)
go('links_minus25')
for l in L0: model2.LINKS[l]=L0[l]
# value of unserved gas doubled
g0,gi0=model2.VOLL_G, model2.VOLL_GI
model2.VOLL_G, model2.VOLL_GI = 1000.0, 500.0
go('vollgas_x2')
model2.VOLL_G, model2.VOLL_GI = g0, gi0
# discount rates
c0=model2.crf
for r_ in (0.06, 0.10):
    model2.DISC=r_; model2.crf=lambda life, r=None, rr=r_: rr*(1+rr)**life/((1+rr)**life-1)
    go(f'disc_{int(r_*100)}')
model2.DISC=0.08; model2.crf=c0
json.dump(out, open('sens3.json','w'), indent=0)

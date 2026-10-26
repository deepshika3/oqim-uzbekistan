import json, pyomo.environ as pe
from model2 import *
out=[]
for cap in [None, 2.5, 2.0, 1.75, 1.5, 1.4, 1.3]:
    m=build(np2025=29.97, eps=None if cap is None else (2030,cap)); r=solve(m, tl=600, gap=0.005)
    if r.best_feasible_objective is None: out.append(dict(cap=cap, feas=False)); print(cap,'inf'); continue
    mx=max(sum(m._pi[w]*pe.value(m.HEP[t,w]) for w in m._S) for t in PLAN if t>=2030)
    row=dict(cap=cap, feas=True, obj=pe.value(m.obj), maxhep=mx, spend=sum(pe.value(m.pubcash[t]) for t in PLAN)); out.append(row); print(row)
json.dump(out, open('frontier3.json','w'))

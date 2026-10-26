import json, time, pyomo.environ as pe
import data2, model2
from model2 import *
from data2 import EENS_PHASE
v=pe.value; out={}
for c in [33.0, 20.0, 12.0, 9.0, 7.5, 6.0]:
    P['BESS']['capex']=c
    t0=time.time(); m=build(np2025=29.97, eens=EENS_PHASE, eps=(2030,1.5)); r=solve(m, tl=900, gap=0.005)
    b=sum(v(m.x[p,n,t]) for (p,n,t) in m.x if p=='BESS')
    out[c]={'bess_units':b,'obj':v(m.obj)}
    print(c, round(time.time()-t0), 'BESS units', round(b,2), 'obj', round(v(m.obj)), flush=True)
    json.dump(out, open('bess_sweep.json','w'))

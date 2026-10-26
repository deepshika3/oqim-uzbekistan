# Value of the barter with the rest of the plan held fixed (all integers fixed -> LP, exact).
import json, pyomo.environ as pe, model2
from model2 import *
v=pe.value
m=build(np2025=29.97, eens=EENS_PHASE, eps=(2030,1.5)); solve(m, tl=900, gap=0.001)
st=stage1(m); print('plan obj', round(v(m.obj),1), 'bs', st['bs'], flush=True)
out={'plan':v(m.obj)}
def ev(name, barter=True, rho=RHO, capex=35.0, bs=None):
    model2.BARTER_CAPEX=capex
    mm=build(np2025=29.97, eens=EENS_PHASE, eps=(2030,1.5), barter=barter, rho=rho)
    for k,x in st['x'].items(): mm.x[k].fix(x)
    for k,x in st['circ'].items(): mm.circ[k].fix(x)
    mm.yK.fix(st['yK'])
    if barter and bs is not None: mm.bs.fix(bs)
    r=solve(mm, tl=600, gap=1e-6)
    if r.best_feasible_objective is None: print(name,'INFEASIBLE'); out[name]=None; return
    out[name]=dict(obj=v(mm.obj), bs=v(mm.bs), ehep=v(mm.EHEP))
    print(name, round(v(mm.obj),1), 'bs', round(v(mm.bs),2), 'EHEP', round(v(mm.EHEP),4), flush=True)
ev('with_barter')
ev('pilot_only_no_expansion', bs=1.0)
ev('no_barter', barter=False)
# re-optimised without the barter
m3=build(np2025=29.97, eens=EENS_PHASE, eps=(2030,1.5), barter=False); solve(m3, tl=900, gap=0.001)
out['nobarter_reopt']=v(m3.obj); print('nobarter_reopt', round(v(m3.obj),1), flush=True)
ev('rho_1.2', rho=1.2)
ev('rho_1.5', rho=1.5)
model2.BARTER_CAPEX=35.0
# 24-month delay without the reliability rule, to see how far service falls
m2=build(np2025=29.97, eens=None, eps=None, lead_add=2); r=solve(m2, tl=900, gap=0.005)
hep={t: round(sum(m2._pi[w]*v(m2.HEP[t,w]) for w in m2._S),2) for t in PLAN}
print('delay24_norules obj', round(v(m2.obj)), 'HEP', hep)
out['delay24_norules']=dict(obj=v(m2.obj), hep=hep)
json.dump(out, open('barterval.json','w'), indent=0, default=float)

# Extra runs: commissioning-delay tests with the target year moved, and barter value at a higher outage value.
import json, pyomo.environ as pe
from model2 import *
v = pe.value; out = {}
def go(name, **kw):
    m = build(np2025=29.97, eens=EENS_PHASE, **kw); r = solve(m, tl=900, gap=0.005)
    if r.best_feasible_objective is None:
        out[name] = None; print(name, 'INFEASIBLE', flush=True); return
    mx = {t: sum(m._pi[w] * v(m.HEP[t, w]) for w in m._S) for t in PLAN}
    out[name] = dict(obj=v(m.obj), spend=sum(v(m.pubcash[t]) for t in PLAN), bs=v(m.bs), hep=mx)
    print(name, 'obj', round(out[name]['obj']), 'spend', round(out[name]['spend']), 'bs', v(m.bs),
          'HEP by year', {t: round(x, 2) for t, x in mx.items()}, flush=True)
for la in (1, 2):
    for y0 in (2031, 2032, 2033):
        go(f'delay{12*la}_target{y0}', lead_add=la, eps=(y0, 1.5))
        if out[f'delay{12*la}_target{y0}']: break
go('voll2000_nobarter', eps=(2030, 1.5), voll_e=2000, barter=False)
json.dump(out, open('extra3.json', 'w'), indent=0, default=float)

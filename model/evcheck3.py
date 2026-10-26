# Best reachable energy-poverty level for the average-future plan ('ev') and the two-stage plan ('plan').
import json, pyomo.environ as pe
from model2 import *
v = pe.value
def full_fix(m, src):
    fx = dict(x={k: 0.0 for k in m.x}, circ={k: 0 for k in m.circ}, yK=0, bs=1.0)
    for k, val in src['x'].items():
        p, n, t = k.split('|'); fx['x'][(p, n, int(t))] = val
    for k, val in src['circ'].items():
        l, t = k.split('|'); fx['circ'][(l, int(t))] = val
    fx['yK'] = src['yK']; fx['bs'] = src['bs']
    return fx
plan = json.load(open('stage1_v3.json'))['plan']
cen = {'MEAN': dict(g=0.056, sup='MID', w='N', p=1.0)}
mev = build(np2025=29.97, scen=cen, eens=EENS_PHASE, eps=(2030, 1.5)); solve(mev, tl=600, gap=0.005)
st_ev = stage1(mev)
out = {}
for name in ('ev', 'plan'):
    m = build(np2025=29.97, eens=None)
    fx = st_ev if name == 'ev' else full_fix(m, plan)
    for k, val in fx['x'].items(): m.x[k].fix(val)
    for k, val in fx['circ'].items(): m.circ[k].fix(val)
    m.yK.fix(fx['yK']); m.bs.fix(fx['bs'])
    m.z = pe.Var()
    m.cz = pe.Constraint([t for t in PLAN if t >= 2030], rule=lambda m, t: sum(m._pi[w] * m.HEP[t, w] for w in m._S) <= m.z)
    m.obj.deactivate(); m.o2 = pe.Objective(expr=m.z); solve(m, tl=300)
    out[name + '_minEHEP'] = v(m.z)
print(out); json.dump(out, open('evcheck3.json', 'w'))

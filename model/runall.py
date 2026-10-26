import time, json, pickle, pyomo.environ as pe
from model2 import *
from data2 import SCEN, EENS_PHASE
NP=29.97; EENS=EENS_PHASE; EPS=(2030,1.5)
v=pe.value
def summarize(m):
    S=m._S; pi=m._pi
    R={}
    R['obj']=v(m.obj); R['ehep']=v(m.EHEP)
    R['x']={f'{p}|{n}|{t}':v(m.x[p,n,t]) for (p,n,t) in m.x if v(m.x[p,n,t])>1e-4}
    R['circ']={f'{l}|{t}':v(m.circ[l,t]) for (l,t) in m.circ if v(m.circ[l,t])>0.5}
    R['yK']=v(m.yK); R['bs']=v(m.bs)
    R['spend']={t:v(m.pubcash[t]) for t in PLAN}
    E=lambda f: {t: sum(pi[w]*f(t,w) for w in S) for t in OPS}
    R['Ue']=E(lambda t,w: sum(v(m.U[n,t,s,h,w]) for n in NODES for s in SEASONS for h in BLOCKS))
    R['UeW_PK_node']={n:{t: sum(pi[w]*v(m.U[n,t,'W','PK',w]) for w in S) for t in OPS} for n in NODES}
    R['Ug']=E(lambda t,w: sum(v(m.Ug[t,s,w]) for s in SEASONS))
    R['Ugi']=E(lambda t,w: sum(v(m.Ugi[t,s,w]) for s in SEASONS))
    R['ugi_scen']={w:{t:sum(v(m.Ugi[t,s,w]) for s in SEASONS) for t in PLAN} for w in S}
    R['ueWPK_scen_node']={w:{n:{t:v(m.U[n,t,'W','PK',w]) for t in PLAN} for n in NODES} for w in S}
    R['imp']=E(lambda t,w: sum(v(m.mRU[t,s,w])+v(m.mTM[t,s,w]) for s in SEASONS))
    R['pg']=E(lambda t,w: sum(v(m.pg[t,s,w]) for s in SEASONS))
    R['coal']=E(lambda t,w: sum(v(m.g['COAL','TAS',t,s,h,w]) for s in SEASONS for h in BLOCKS))
    R['dKG']=E(lambda t,w: v(m.dKG[t,w])); R['dUZ']=E(lambda t,w: v(m.dUZ[t,w]))
    gen={}
    for k in K0: gen[k]=E(lambda t,w,k=k: sum(v(m.g[k,n,t,s,h,w]) for n in K0[k] for s in SEASONS for h in BLOCKS))
    gen['HYD']=E(lambda t,w: sum(v(m.hyd[n,t,s,h,w]) for n in HYDN for s in SEASONS for h in BLOCKS))
    gen['SOL']=E(lambda t,w: sum(v(m.sol[n,t,s,h,w]) for n in NODES for s in SEASONS for h in BLOCKS))
    gen['WND']=E(lambda t,w: sum(v(m.wnd[n,t,s,h,w]) for n in WND_NODE for s in SEASONS for h in BLOCKS))
    gen['NUC']=E(lambda t,w: sum(v(m.nuc[t,s,h,w]) for s in SEASONS for h in BLOCKS))
    gen['KAM']=E(lambda t,w: sum(v(m.kam[t,s,h,w]) for s in SEASONS for h in BLOCKS))
    gen['IMP']=E(lambda t,w: sum(v(m.ei[n,t,s,h,w]) for n in ('TAS','STH') for s in SEASONS for h in BLOCKS))
    R['gen']=gen
    R['hep_scen']={w:{t:v(m.HEP[t,w]) for t in PLAN} for w in S}
    R['ug_scen']={w:{t:sum(v(m.Ug[t,s,w]) for s in SEASONS) for t in PLAN} for w in S}
    R['ue_scen']={w:{t:sum(v(m.U[n,t,s,h,w]) for n in NODES for s in SEASONS for h in BLOCKS) for t in PLAN} for w in S}
    R['flows']={}
    R['inv']={t:v(m.INV[t]) for t in OPS}; R['opx']={t:sum(pi[w]*v(m.OPX[t,w]) for w in S) for t in OPS}
    return R
res={}
def run(name, **kw):
    t0=time.time(); m=build(np2025=NP, **kw); r=solve(m, tl=900, gap=0.005)
    if r.best_feasible_objective is None:
        print(name,'INFEASIBLE'); res[name]=None; return None
    R=summarize(m); res[name]=R
    print(name, round(time.time()-t0),'s obj',round(R['obj']),'EHEP',round(R['ehep'],3),'spend',round(sum(R['spend'].values())),'yK',R['yK'],'bs',R['bs'],flush=True)
    return m
# 1 plan (risk-neutral, eps)
m=run('plan', eens=EENS, eps=EPS); st_plan=stage1(m)
# 2 baseline: no new projects (committed only)
zero=dict(x={k:0 for k in m.x}, circ={k:0 for k in m.circ}, yK=0)
run('base', eens=None, fix=zero, barter=False)
# 3 cost-only (no eps)
run('costonly', eens=EENS)
# 4 risk-averse: CVaR(0.9) of scenario-average HEP
pi=m._pi
cv_plan = None
import numpy as np
hs=sorted([(sum(res['plan']['hep_scen'][w].values())/len(PLAN), pi[w]) for w in m._S], reverse=True)
acc=0; tail=0
for h,p in hs:
    take=min(p, 0.1-acc); tail+=take*h; acc+=take
    if acc>=0.1-1e-9: break
cv_plan=tail/0.1; print('plan CVaR90', cv_plan)
res['plan_cvar90']=cv_plan
for frac in (0.9, 0.8):
    run(f'cvar_{frac}', eens=EENS, eps=EPS, cvar=(0.9, frac*cv_plan))
# 5 EV (deterministic central) -> evaluate
cen={'MEAN': dict(g=0.056, sup='MID', w='N', p=1.0)}
mev=build(np2025=NP, scen=cen, eens=EENS, eps=EPS); r=solve(mev, tl=600, gap=0.005)
st_ev=stage1(mev); res['ev_design']=summarize(mev)
run('EEV', eens=None, fix=st_ev)
run('RP_noeens_eval', eens=None, fix=st_plan)
# 6 wait-and-see
ws=0; wsh=0
for w in SCEN:
    mw=build(np2025=NP, scen={w:SCEN[w]}, eens=EENS, eps=None); r=solve(mw, tl=300, gap=0.005)
    if r.best_feasible_objective is None:
        mw=build(np2025=NP, scen={w:SCEN[w]}, eens=None); r=solve(mw, tl=300, gap=0.005)
    ws+=SCEN[w]['p']*v(mw.obj); wsh+=SCEN[w]['p']*v(mw.EHEP)
res['WS']=dict(obj=ws, ehep=wsh); print('WS',ws)
# 7 sensitivities
run('sens_voll2000', eens=EENS, eps=EPS, voll_e=2000)
run('sens_kamb2031', eens=EENS, eps=EPS, kamb_online=2031)
run('sens_nucdelay', eens=EENS, eps=EPS, nuc={2032:0.055,2033:0.110,2036:1.110,2038:2.110})
run('sens_nobarter', eens=EENS, eps=EPS, barter=False)
run('sens_delay12', eens=EENS, eps=EPS, lead_add=1)
run('sens_delay24', eens=EENS, eps=EPS, lead_add=2)
run('sens_eps2', eens=EENS, eps=(2030,2.0))
json.dump(res, open('results3.json','w'), indent=0, default=float)
json.dump(dict(plan={'x':{'|'.join(map(str,k)):v for k,v in st_plan['x'].items() if v>1e-6},'circ':{'|'.join(map(str,k)):v for k,v in st_plan['circ'].items() if v},'yK':st_plan['yK'],'bs':st_plan['bs']}), open('stage1_v3.json','w'), indent=0)

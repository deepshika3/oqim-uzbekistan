# Back-cast 2025: dispatch the 2025 fleet against 2025 demand and compare with actual statistics.
import pyomo.environ as pe, json
from data2 import *
from model2 import GAS_DOM, delta

K25 = {k: dict(v) for k, v in K0.items()}
K25['CCGT']['TAS'] -= 1.573; K25['CCGT']['STH'] -= 1.56     # Syrdarya-2 and Angor not yet online
KS, KW, KB = 3.2, 1.3, 1.0   # mid-2025 average solar, wind, battery GW [CALC from 2024-25 additions]
LOAD = D_DOM_2025 + 4.1      # domestic requirement + all exports
m = pe.ConcreteModel()
TH = [(k, n) for k in K25 for n in K25[k]]
I = [(s, h) for s in SEASONS for h in BLOCKS]
m.g = pe.Var(TH, I, within=pe.NonNegativeReals)
m.hy = pe.Var(I, within=pe.NonNegativeReals); m.so = pe.Var(I, within=pe.NonNegativeReals)
m.wi = pe.Var(I, within=pe.NonNegativeReals); m.bd = pe.Var(I, within=pe.NonNegativeReals)
m.bc = pe.Var(I, within=pe.NonNegativeReals); m.U = pe.Var(I, within=pe.NonNegativeReals)
m.im = pe.Var(I, within=pe.NonNegativeReals)
m.c = pe.ConstraintList()
for (s, h) in I:
    dl = delta(s, h)
    D = LOAD * DAYMULT[s] * SEASONS[s] / 365 * BLOCKS[h] * BLOCK_MULT[h] / 24
    m.c.add(sum(m.g[k, n, s, h] for (k, n) in TH) + m.hy[s, h] + m.so[s, h] + m.wi[s, h] + m.bd[s, h] - m.bc[s, h]
            + m.im[s, h] + m.U[s, h] == D)
    for (k, n) in TH: m.c.add(m.g[k, n, s, h] <= AV[k][s] * K25[k][n] * dl)
    m.c.add(m.hy[s, h] <= K_HYD0 * dl)
    m.c.add(m.so[s, h] <= KS * CF_SOL[s] * 24 * SOL_BLOCKSHARE[s][h] * SEASONS[s] / 1000)
    m.c.add(m.wi[s, h] <= KW * CF_WND[s] * dl)
    if h == 'PK': m.c.add(m.bd[s, h] <= KB * 2 * SEASONS[s] / 1000); m.c.add(m.bc[s, h] == 0)
    else: m.c.add(m.bd[s, h] == 0)
MR=MUSTRUN_OLD_W
for (k,n) in TH:
    if k=='OLDG':
        for h in BLOCKS: m.c.add(m.g[k,n,'W',h] >= MR*AV[k]['W']*K25[k][n]*delta('W',h))
for s in SEASONS:
    m.c.add(sum(m.hy[s, h] for h in BLOCKS) <= E_HYD[s] * DRY['C'])   # 2025 was a dry year
    m.c.add(sum(m.bc[s, h] for h in BLOCKS) == m.bd[s, 'PK'] / ETA_B)
m.c.add(sum(m.im[i] for i in I) <= 0.9)
pg = sum(HR[k] * m.g[k, n, s, h] for (k, n) in TH if k in GASFIRED for (s, h) in I) / 35.8
m.o = pe.Objective(expr=GAS_DOM * pg + COAL_COST * sum(m.g['COAL', 'TAS', s, h] for (s, h) in I)
                   + 20 * sum(m.im[i] for i in I) + 2000 * sum(m.U[i] for i in I))
pe.SolverFactory('appsi_highs').solve(m)
v = pe.value
out = dict(
    thermal=sum(v(m.g[k, n, i]) for (k, n) in TH for i in I),
    coal=sum(v(m.g['COAL', 'TAS', i]) for i in I),
    solar_wind=sum(v(m.so[i]) + v(m.wi[i]) for i in I),
    hydro=sum(v(m.hy[i]) for i in I), imports=sum(v(m.im[i]) for i in I),
    unserved=sum(v(m.U[i]) for i in I), power_gas=v(pg),
    by_class={k: sum(v(m.g[k, n, i]) for n in K25[k] for i in I) for k in K25})
out['generation'] = out['thermal'] + out['solar_wind'] + out['hydro']
out['nonpower_gas_2025'] = GAS_DEMAND_2025 - out['power_gas']
out['actual'] = dict(generation=86.7, thermal=69.9, solar_wind=10.5, hydro=6.3,
                     power_gas_IEA_share=0.37 * 44.5)
json.dump(out, open('validation.json', 'w'), indent=1)
print(json.dumps(out, indent=1))

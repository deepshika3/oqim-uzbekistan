import pyomo.environ as pe
from data2 import *

GAS_DOM = 58.0          # MUSD/bcm, production cost (Condor Energies 2025: USD 1.63/Mcf) [SRC]
IMP_PREM = IMP_PRICE - GAS_DOM

def crf(life, r=DISC):
    return r * (1 + r) ** life / ((1 + r) ** life - 1)

def delta(s, h):
    return SEASONS[s] * BLOCKS[h] / 1000.0      # TWh per GW

def capex(p, t):
    c = P[p]['capex']
    lr = P[p].get('learn', 0.0)
    return c * (1 - lr) ** (t - 2024)

def pnodes(p):
    return P[p]['nodes'] or ['ALL']

THERM = [(k, n) for k in K0 for n in K0[k]]
HYDN = [n for n in NODES if HYD_NODE.get(n, 0) > 0]


def build(scen=None, eps=None, budget=BUDGET, fix=None, cvar=None, voll_e=VOLL_E, np2025=None,
          rho=RHO, kamb_online=KAMB_ONLINE, nuc=NUC, barter=True, lead_add=0, eens=EENS_PHASE, prob=None):
    scen = scen or SCEN
    m = pe.ConcreteModel()
    S = list(scen)
    pi = {w: (prob(scen[w]) if prob else scen[w]['p']) for w in S}
    tot = sum(pi.values()); pi = {w: pi[w] / tot for w in S}
    NP0 = np2025
    # ---------------- stage 1 ----------------
    XI = [(p, n, t) for p in P for n in pnodes(p) for t in PLAN]
    m.x = pe.Var(XI, within=pe.NonNegativeReals)
    for (p, n, t) in XI:
        if P[p].get('integer'):
            m.x[p, n, t].domain = pe.NonNegativeIntegers
    m.circ = pe.Var(list(LINKS), PLAN, within=pe.NonNegativeIntegers, bounds=(0, 2))
    m.yK = pe.Var(within=pe.Binary)
    # barter: pilot volumes fixed 2027-2029; scale factor bs (1 to 2) chosen for 2030 onward
    m.bs = pe.Var(bounds=(1, BARTER_SCALE_MAX) if barter else (0, 0), initialize=1 if barter else 0)
    if not barter: m.bs.fix(0)

    def tp(t): return min(t, PLAN[-1])
    def Xb(p, n, t):   # built (started) up to t
        return sum(m.x[p, n, tau] for tau in PLAN if tau <= t)
    def Xo(p, n, t):   # operating in t (lead_add = extra commissioning delay in years, stress test)
        return sum(m.x[p, n, tau] for tau in PLAN if tau <= t - P[p]['lead'] - lead_add)
    def XoAll(p, t):
        return sum(Xo(p, n, t) for n in pnodes(p))
    def bsc(t):        # barter scale in year t (0 if no barter)
        if not barter: return 0
        return 1 if t < BARTER_FROM else m.bs
    def o(t): return m.yK if t >= kamb_online else 0
    def circ_on(l, t): return sum(m.circ[l, tau] for tau in PLAN if tau <= t - 3 - lead_add)

    # C1 build limits
    m.gmax = pe.ConstraintList(); m.pot = pe.ConstraintList()
    for p in P:
        for t in PLAN:
            m.gmax.add(sum(m.x[p, n, t] for n in pnodes(p)) <= P[p]['gmax'])
        for n in pnodes(p):
            m.pot.add(sum(m.x[p, n, t] for t in PLAN) <= P[p]['pot'])
    for l in LINKS:
        m.pot.add(sum(m.circ[l, t] for t in PLAN) <= 3)
    # REPW can only rebuild existing old units
    for n in P['REPW']['nodes']:
        m.pot.add(0.45 * sum(m.x['REPW', n, t] for t in PLAN) <= K0['OLDG'][n])

    # C13 budget (public cash, plan years)
    def pubcash(t):
        e = sum(P[p]['pub'] * capex(p, t) * m.x[p, n, t] for p in P for n in pnodes(p))
        e += sum(LINE_COST * LINKS[l][3] * m.circ[l, t] for l in LINKS)
        if t in KAMB_SPEND:
            e += m.yK * KAMB_COST_UZ / len(KAMB_SPEND)
        if barter:
            e += BARTER_ADMIN + (BARTER_CAPEX if t == PLAN[0] else 0)
            if t == BARTER_EXP_YEAR: e += BARTER_EXP_CAPEX * (m.bs - 1)
        return e
    m.pubcash = pe.Expression(PLAN, rule=lambda m, t: pubcash(t))
    m.bud = pe.Constraint(expr=sum(m.pubcash[t] for t in PLAN) <= budget)
    m.budyr = pe.Constraint(PLAN, rule=lambda m, t: m.pubcash[t] <= BUDGET_YR)

    # derived capacities
    def Kth(k, n, t):
        e = K0[k][n] + sum(v for (kk, nn, yy), v in COMMITTED.items() if kk == k and nn == n and t >= yy)
        if n in P['REPW']['nodes']:
            if k == 'OLDG':
                e = e - 0.45 * Xb('REPW', n, t)
            if k == 'CCGT':
                e = e + 0.45 * Xo('REPW', n, t)
        return e
    def Khyd(n, t):
        e = K_HYD0 * HYD_NODE[n] + (sum(v for y, v in COMMITTED_HYD.items() if t >= y) if n == 'TAS' else 0)
        if n in P['HYD']['nodes']:
            e = e + 0.1 * Xo('HYD', n, t)
        return e
    def Ksol(n, t):
        e = K_SOL0 * SOL_NODE.get(n, 0)
        if n in P['SOLAR']['nodes']: e = e + 0.1 * Xo('SOLAR', n, t)
        return e
    def Kwnd(n, t):
        e = K_WND0 * WND_NODE.get(n, 0)
        if n in P['WIND']['nodes']: e = e + 0.1 * Xo('WIND', n, t)
        return e
    def Kbes(n, t): return K_BES0 * SOL_NODE.get(n, 0) + 0.1 * Xo('BESS', n, t)
    def Kdist(n, t): return DIST_HEADROOM * PEAK_2025 * NSHARE[n] + 0.1 * Xo('DIST', n, t)
    def Knuc(t):
        vals = [v for y, v in nuc.items() if y <= t]
        return max(vals) if vals else 0
    def lossred(t): return LOSS_PER_DIST * sum(Xo('DIST', n, t) for n in NODES) / (1 - LOSS0)
    def WELLgas(t):
        return sum(m.x['WELL', 'ALL', tau] * WELL_GAS0 * (1 - WELL_DECL) ** (t - tau - 1)
                   for tau in PLAN if 1 + lead_add <= t - tau < P['WELL']['life'] + lead_add)
    def gas_proj(t): return METH_GAS * XoAll('METH', t) + WELLgas(t)
    def sav(s, t):
        if s == 'W':
            return (0.9 * DH_GAS * XoAll('DH', t) + BOIL_GAS * XoAll('BOIL', t) + INSUL_GAS * XoAll('INSUL', t)
                    + HP_GAS * XoAll('HPUMP', t))
        if s == 'SH':
            return 0.1 * DH_GAS * XoAll('DH', t)
        return 0
    UGS = lambda t: UGS0 + UGS_BLOCK * XoAll('UGS', t)

    # ---------------- stage 2 ----------------
    TS = [(t, s, w) for t in OPS for s in SEASONS for w in S]
    TSH = [(t, s, h, w) for t in OPS for s in SEASONS for h in BLOCKS for w in S]
    m.g = pe.Var([(k, n) + i for (k, n) in THERM for i in TSH], within=pe.NonNegativeReals)
    m.hyd = pe.Var([(n,) + i for n in HYDN for i in TSH], within=pe.NonNegativeReals)
    m.sol = pe.Var([(n,) + i for n in NODES for i in TSH], within=pe.NonNegativeReals)
    m.wnd = pe.Var([(n,) + i for n in WND_NODE for i in TSH], within=pe.NonNegativeReals)
    m.bd = pe.Var([(n,) + i for n in NODES for i in TSH], within=pe.NonNegativeReals)
    m.bc = pe.Var([(n,) + i for n in NODES for i in TSH], within=pe.NonNegativeReals)
    m.U = pe.Var([(n,) + i for n in NODES for i in TSH], within=pe.NonNegativeReals)
    m.ei = pe.Var([(n,) + i for n in ['TAS', 'STH'] for i in TSH], within=pe.NonNegativeReals)
    m.nuc = pe.Var(TSH, within=pe.NonNegativeReals)
    m.kam = pe.Var(TSH, within=pe.NonNegativeReals)
    m.f = pe.Var([(l,) + i for l in LINKS for i in TSH], within=pe.Reals)
    m.mRU = pe.Var(TS, within=pe.NonNegativeReals); m.mTM = pe.Var(TS, within=pe.NonNegativeReals)
    m.qi = pe.Var(TS, within=pe.NonNegativeReals); m.qo = pe.Var(TS, within=pe.NonNegativeReals)
    m.Ug = pe.Var(TS, within=pe.NonNegativeReals); m.Ugi = pe.Var(TS, within=pe.NonNegativeReals); m.spill = pe.Var(TS, within=pe.NonNegativeReals)
    TW = [(t, w) for t in OPS for w in S]
    m.dKG = pe.Var(TW, within=pe.NonNegativeReals)   # Kazakh winter power delivered to Kyrgyzstan (TWh)
    m.dUZ = pe.Var(TW, within=pe.NonNegativeReals)   # Kazakh winter-peak power delivered to Uzbekistan (TWh)
    def kgret(t, w):   # Kyrgyz return scales with the Kyrgyz leg actually delivered
        return m.dKG[t, w] / BARTER_KG
    m.UdE = pe.Var(TW, within=pe.NonNegativeReals); m.UdG = pe.Var(TW, within=pe.NonNegativeReals); m.UdGi = pe.Var(TW, within=pe.NonNegativeReals)

    def Dn(n, t, s, h, w):
        sc = scen[w]
        ann = D_DOM_2025 * (1 + sc['g']) ** (min(t, PLAN[-1]) - 2025)
        e = ann * DAYMULT[s] * SEASONS[s] / 365 * BLOCKS[h] * BLOCK_MULT[h] / 24 * NSHARE[n]
        if s == 'W': e *= COLD_EL[sc['w']]
        return e
    def extra(n, t, s, h, w):   # load changes from projects and contracts
        e = 0
        if n == 'STH': e += AF_EXPORT * SEASONS[s] / 365 * BLOCKS[h] / 24
        if s == 'W': e += HP_EL * HP_BLOCK[h] * PSHARE[n] * XoAll('HPUMP', t)
        pv = RT_PV * CF_SOL[s] * 24 / 1000 * SEASONS[s]
        if h == 'DAY': e += Xo('RTSOL', n, t) * (-pv * SOL_BLOCKSHARE[s]['DAY'] + RT_BATT * SEASONS[s] / 0.9)
        if h == 'PK': e += Xo('RTSOL', n, t) * (-pv * SOL_BLOCKSHARE[s]['PK'] - RT_BATT * SEASONS[s])
        if s in PUMP_SEAS: e -= 0.1 * PUMP_SEAS[s] * BLOCKS[h] / 24 * PSHARE[n] * XoAll('PUMP', t)
        if n == 'TAS' and h == 'DAY' and s in REPAY_SPLIT:          # Uzbek summer repayment to Kazakhstan
            e += rho * (m.dKG[t, w] + m.dUZ[t, w]) * REPAY_SPLIT[s]
        return e
    def load(n, t, s, h, w):
        return Dn(n, t, s, h, w) * (1 - lossred(t)) + extra(n, t, s, h, w)

    m.ebal = pe.ConstraintList(); m.lim = pe.ConstraintList()
    for (t, s, h, w) in TSH:
        dl = delta(s, h)
        for n in NODES:
            sup = sum(m.g[k, n, t, s, h, w] for k in K0 if n in K0[k])
            if n in HYDN: sup += m.hyd[n, t, s, h, w]
            if n in WND_NODE: sup += m.wnd[n, t, s, h, w]
            if n in ('TAS', 'STH'): sup += m.ei[n, t, s, h, w]
            if n == 'TAS': sup += m.nuc[t, s, h, w]
            if n == 'FER': sup += m.kam[t, s, h, w]
            if n == 'TAS' and s == 'W' and h == 'PK': sup += m.dUZ[t, w]          # Kazakh winter-peak block
            if n == 'FER' and h == 'DAY' and s in KG_HYDRO_SPLIT:                  # Kyrgyz summer hydro
                sup += KG_HYDRO * KG_HYDRO_SPLIT[s] * kgret(t, w)
            sup += m.sol[n, t, s, h, w] + m.bd[n, t, s, h, w] - m.bc[n, t, s, h, w] + m.U[n, t, s, h, w]
            flow = sum(m.f[l, t, s, h, w] for l in LINKS if LINKS[l][1] == n) - \
                   sum(m.f[l, t, s, h, w] for l in LINKS if LINKS[l][0] == n)
            m.ebal.add(sup + flow == load(n, t, s, h, w))
            # plant limits
            for k in K0:
                if n in K0[k]:
                    m.lim.add(m.g[k, n, t, s, h, w] <= AV[k][s] * Kth(k, n, t) * dl)
                    if k == 'OLDG' and s == 'W':
                        m.lim.add(m.g[k, n, t, s, h, w] >= MUSTRUN_OLD_W * AV[k][s] * Kth(k, n, t) * dl)
            if n in HYDN: m.lim.add(m.hyd[n, t, s, h, w] <= Khyd(n, t) * dl)
            m.lim.add(m.sol[n, t, s, h, w] <= Ksol(n, t) * CF_SOL[s] * 24 * SOL_BLOCKSHARE[s][h] * SEASONS[s] / 1000)
            if n in WND_NODE: m.lim.add(m.wnd[n, t, s, h, w] <= Kwnd(n, t) * CF_WND[s] * dl)
            if h == 'PK':
                m.lim.add(m.bd[n, t, s, h, w] <= Kbes(n, t) * min(BESS_H, BLOCKS[h]) * SEASONS[s] / 1000)
                m.lim.add(m.bc[n, t, s, h, w] == 0)
                # distribution limit at the peak hour
                m.lim.add((load(n, t, s, h, w) - m.U[n, t, s, h, w]) * PEAK_RATIO / BLOCK_MULT['PK'] <= Kdist(n, t) * dl)
            else:
                m.lim.add(m.bd[n, t, s, h, w] == 0)
            if n in ('TAS', 'STH') and h == 'PK':
                m.lim.add(m.ei[n, t, s, h, w] <= EIMP_PK / 2 * EIMP_CUT[scen[w]['w']] * dl)
        m.lim.add(m.nuc[t, s, h, w] <= Knuc(t) * 0.9 * dl)
        m.lim.add(m.kam[t, s, h, w] <= KAMB_K * dl * o(t))
        for l in LINKS:
            cap = (LINKS[l][2] + CIRCUIT * circ_on(l, t)) * dl
            m.lim.add(m.f[l, t, s, h, w] <= cap); m.lim.add(-m.f[l, t, s, h, w] <= cap)
    for (t, s, w) in TS:
        sc = scen[w]
        for n in NODES:
            m.lim.add(sum(m.bc[n, t, s, h, w] for h in BLOCKS) == m.bd[n, t, s, 'PK', w] / ETA_B)
        for n in HYDN:
            E = E_HYD[s] * HYD_NODE[n] * DRY[sc['w']]
            newK = (0.40 if (n == 'TAS' and t >= 2028) else 0)
            if n in P['HYD']['nodes']: newK = newK + 0.1 * Xo('HYD', n, t)
            E = E + newK * HYD_CF * 8.76 * HYD_SHAPE[s] * DRY[sc['w']]
            m.lim.add(sum(m.hyd[n, t, s, h, w] for h in BLOCKS) <= E)
        m.lim.add(sum(m.kam[t, s, h, w] for h in BLOCKS) <= KAMB_E * KAMB_SHAPE[s] * o(t))
        for n in ('TAS', 'STH'):
            m.lim.add(sum(m.ei[n, t, s, h, w] for h in BLOCKS) <= EIMP[s] / 2 * EIMP_CUT[sc['w']])

    # gas
    def powergas(t, s, w):
        return sum(HR[k] * m.g[k, n, t, s, h, w] for (k, n) in THERM if k in GASFIRED for h in BLOCKS) / 35.8
    m.pg = pe.Expression(TS, rule=lambda m, t, s, w: powergas(t, s, w))
    def NP(t, s, w):
        e = NP0 * (1 + G_NP) ** (min(t, PLAN[-1]) - 2025) * NP_SHAPE[s]
        if s == 'W': e *= COLD_GAS[scen[w]['w']]
        return e
    m.gbal = pe.ConstraintList()
    for (t, s, w) in TS:
        sc = scen[w]
        fs = SEASONS[s] / 365
        m.gbal.add(gas_prod(min(t, PLAN[-1]), sc['sup']) * fs + gas_proj(t) * fs + m.mRU[t, s, w] + m.mTM[t, s, w]
                   + m.qo[t, s, w] - m.qi[t, s, w] + m.Ug[t, s, w] + m.Ugi[t, s, w] - m.spill[t, s, w]
                   == NP(t, s, w) - sav(s, t) + m.pg[t, s, w])
        m.gbal.add(m.Ugi[t, s, w] <= IND_SHARE * NP(t, s, w))
        m.gbal.add(m.mRU[t, s, w] <= (ru_day(t) - (RU_CUT_X if (s == 'W' and sc['w'] == 'X') else 0)) * SEASONS[s])
        m.gbal.add(m.mTM[t, s, w] <= (0 if (s == 'W' and sc['w'] == 'X') else TM_DAY * SEASONS[s]))
        if s == 'W':
            m.gbal.add(m.qi[t, s, w] == 0)
            m.gbal.add(m.qo[t, s, w] <= UGS(t))
            m.gbal.add(m.qo[t, s, w] <= (UGS0_WD + UGS_WD_PER_BCM * UGS_BLOCK * XoAll('UGS', t)) * SEASONS[s])
        else:
            m.gbal.add(m.qo[t, s, w] == 0)
    for (t, w) in TW:
        sc = scen[w]
        m.gbal.add(sum(m.mRU[t, s, w] for s in SEASONS) <= ru_cap(t))
        m.gbal.add(sum(m.mTM[t, s, w] for s in SEASONS) <= TM_CAP)
        m.gbal.add(sum(m.qi[t, s, w] for s in SEASONS) == m.qo[t, 'W', w])
        # barter
        m.gbal.add(m.dKG[t, w] == BARTER_KG * bsc(t) * KZ_AVAIL[sc['w']])
        m.gbal.add(m.dUZ[t, w] == BARTER_UZ * bsc(t) * KZ_AVAIL[sc['w']])
        m.gbal.add(m.dUZ[t, w] <= BARTER_UZ_MW * bsc(t) * delta('W', 'PK'))
        # design cold day: gas (bcm/day)
        supply = (gas_prod(min(t, PLAN[-1]), sc['sup']) + gas_proj(t)) / 365 + ru_day(t) - (RU_CUT_X if sc['w'] == 'X' else 0) + (0 if sc['w'] == 'X' else TM_DAY) \
                 + UGS0_WD + UGS_WD_PER_BCM * UGS_BLOCK * XoAll('UGS', t)
        dem = NP(t, 'W', w) / 151 * DD_NP - sav('W', t) / 151 + m.pg[t, 'W', w] / 151 * DD_PG
        m.gbal.add(supply + m.UdG[t, w] + m.UdGi[t, w] >= dem)
        m.gbal.add(m.UdGi[t, w] <= IND_SHARE * NP(t, 'W', w) / 151 * DD_NP)
        # design cold day: electricity peak hour (GW)
        firm = sum(AV[k]['W'] * Kth(k, n, t) for (k, n) in THERM) + 0.9 * sum(Khyd(n, t) for n in HYDN) \
               + sum(Kbes(n, t) for n in NODES) + 0.0125 * XoAll('RTSOL', t) \
               + WIND_CREDIT * sum(Kwnd(n, t) for n in WND_NODE) + KAMB_K * o(t) + 0.9 * Knuc(t) \
               + EIMP_PK * EIMP_CUT[sc['w']] + BARTER_UZ_MW * bsc(t) * KZ_AVAIL[sc['w']]
        hp_pk = HP_EL * HP_BLOCK['PK'] / delta('W', 'PK') * PEAK_RATIO
        peak = PEAK_2026 * (1 + sc['g']) ** (min(t, PLAN[-1]) - 2026) * COLD_EL[sc['w']] * (1 - lossred(t)) + hp_pk * XoAll('HPUMP', t) \
               + (AF_EXPORT / 8.76)
        m.gbal.add(firm + m.UdE[t, w] >= peak)

    # ---------------- energy-poverty metric (million households) ----------------
    def HEP(t, w):
        a = HH_PER_BCM * m.Ug[t, 'W', w]
        b = HH * sum(m.U[n, t, 'W', 'PK', w] for n in NODES) / sum(Dn(n, t, 'W', 'PK', w) for n in NODES)
        c = HH_OFFGAS - 0.01 * XoAll('STOVE', t)
        dd = m.UdG[t, w] * 1e9 / HH_DD_M3 / 1e6 * N_DD[scen[w]['w']] / 151
        return a + b + c + dd
    m.HEP = pe.Expression(TW, rule=lambda m, t, w: HEP(t, w))
    m.EHEP = pe.Expression(expr=sum(pi[w] * m.HEP[t, w] for t in PLAN for w in S) / len(PLAN))
    # reliability standard: expected unserved energy share (EENS) [ASM, following Zampara et al. 2025]
    if eens is not None:
        m.eensc = pe.ConstraintList()
        for t in PLAN:
            lims = [l for (a, b2, l) in eens if a <= t <= b2]
            if not lims: continue
            lim = lims[0]
            m.eensc.add(sum(pi[w] * m.U[n, t, s, h, w] for w in S for n in NODES for s in SEASONS for h in BLOCKS)
                        <= lim * sum(pi[w] * Dn(n, t, s, h, w) for w in S for n in NODES for s in SEASONS for h in BLOCKS))
    if eps is not None:
        if isinstance(eps, list):       # [(from_year, cap), ...]: tightening caps over time
            def capt(t):
                cs=[c for (y0, c) in eps if t >= y0]
                return min(cs) if cs else None
            m.epsc = pe.Constraint([t for t in PLAN if capt(t) is not None],
                                   rule=lambda m, t: sum(pi[w] * m.HEP[t, w] for w in S) <= capt(t))
        elif isinstance(eps, tuple):      # (from_year, cap): expected HEP in every year from from_year
            m.epsc = pe.Constraint([t for t in PLAN if t >= eps[0]],
                                   rule=lambda m, t: sum(pi[w] * m.HEP[t, w] for w in S) <= eps[1])
        else:
            m.epsc = pe.Constraint(expr=m.EHEP <= eps)
    if cvar is not None:
        alpha, kappa = cvar
        m.eta = pe.Var(); m.z = pe.Var(S, within=pe.NonNegativeReals)
        m.cz = pe.Constraint(S, rule=lambda m, w: m.z[w] >= sum(m.HEP[t, w] for t in PLAN) / len(PLAN) - m.eta)
        m.cv = pe.Constraint(expr=m.eta + sum(pi[w] * m.z[w] for w in S) / (1 - alpha) <= kappa)

    # ---------------- objective ----------------
    def inv(t):
        e = 0
        for p in P:
            for n in pnodes(p):
                for tau in PLAN:
                    if tau <= t and t - tau < P[p]['life']:
                        e += m.x[p, n, tau] * capex(p, tau) * crf(P[p]['life'])
                e += P[p]['om'] * P[p]['capex'] * Xo(p, n, t)
        e += sum(LINE_COST * LINKS[l][3] * m.circ[l, tau] * crf(40) for l in LINKS for tau in PLAN if tau <= t)
        if t >= kamb_online: e += m.yK * KAMB_COST_UZ * crf(40)
        if barter:
            e += BARTER_CAPEX * crf(20) + (BARTER_ADMIN if t in PLAN else 0)
            if t >= BARTER_EXP_YEAR: e += BARTER_EXP_CAPEX * (m.bs - 1) * crf(40)
        return e
    def opx(t, w):
        e = IMP_PREM * sum(m.mRU[t, s, w] + m.mTM[t, s, w] for s in SEASONS)
        e += GAS_DOM * sum(m.pg[t, s, w] for s in SEASONS)
        e += COAL_COST * sum(m.g['COAL', 'TAS', t, s, h, w] for s in SEASONS for h in BLOCKS)
        e += EIMP_PRICE * sum(m.ei[n, t, s, h, w] for n in ('TAS', 'STH') for s in SEASONS for h in BLOCKS)
        e += voll_e * sum(m.U[n, t, s, h, w] for n in NODES for s in SEASONS for h in BLOCKS)
        e += VOLL_G * sum(m.Ug[t, s, w] for s in SEASONS) + VOLL_GI * sum(m.Ugi[t, s, w] for s in SEASONS)
        e += VOLL_GI * m.UdGi[t, w] * N_DD[scen[w]['w']]
        e += voll_e * m.UdE[t, w] * 4 * N_DD[scen[w]['w']] / 1000 + VOLL_G * m.UdG[t, w] * N_DD[scen[w]['w']]
        e -= WATER_VAL * KG_WATER * kgret(t, w)          # value of the extra irrigation water to Uzbekistan
        return e
    m.INV = pe.Expression(OPS, rule=lambda m, t: inv(t))
    m.OPX = pe.Expression(TW, rule=lambda m, t, w: opx(t, w))
    df = {t: (1 + DISC) ** -(t - 2027) for t in OPS}
    m.obj = pe.Objective(expr=sum(df[t] * (m.INV[t] + sum(pi[w] * m.OPX[t, w] for w in S)) for t in OPS))

    if fix:
        for k, v in fix['x'].items(): m.x[k].fix(v)
        for k, v in fix['circ'].items(): m.circ[k].fix(v)
        m.yK.fix(fix['yK'])
        if barter and 'bs' in fix: m.bs.fix(fix['bs'])
    m._pi = pi; m._S = S; m._scen = scen
    return m


def solve(m, tl=900, gap=0.002, verbose=False):
    from pyomo.contrib.appsi.solvers import Highs
    opt = Highs()
    opt.config.time_limit = tl
    opt.config.mip_gap = gap
    opt.config.stream_solver = verbose
    opt.config.load_solution = False
    res = opt.solve(m)
    if res.best_feasible_objective is not None:
        res.solution_loader.load_vars()
    return res


def stage1(m):
    return dict(x={k: round(pe.value(m.x[k]), 6) for k in m.x},
                circ={k: round(pe.value(m.circ[k])) for k in m.circ},
                yK=round(pe.value(m.yK)), bs=pe.value(m.bs))

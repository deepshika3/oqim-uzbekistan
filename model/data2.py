# Uzbekistan two-stage stochastic planning model, version 2 (real data).
# Units: money USD million (MUSD), energy TWh, power GW, gas bcm.
# Tags in comments: [SRC] sourced value, [CALC] own calculation from sourced values,
# [ASM] assumption (no published value found; closest proxy named).
import itertools

PLAN = list(range(2027, 2037))          # build decisions
OPS = list(range(2027, 2041))           # operations (2037-40 added so late builds are valued: end-of-horizon fix)
SEASONS = {'W': 151, 'SH': 122, 'SU': 92}   # Nov-Mar, Apr-May+Sep-Oct, Jun-Aug
BLOCKS = {'DAY': 9, 'PK': 4, 'NT': 11}      # 08-17, 17-21 evening peak, 21-08
NODES = ['TAS', 'FER', 'CEN', 'STH', 'WST']
NODE_NAME = {'TAS': 'Tashkent city+region, Syrdarya, Jizzakh', 'FER': 'Fergana, Andijan, Namangan',
             'CEN': 'Samarkand, Navoi, Bukhara', 'STH': 'Kashkadarya, Surkhandarya',
             'WST': 'Karakalpakstan, Khorezm'}
# 2025 consumption by subscribers, GWh (SIAT indicator 1.02.02.0019) [SRC] -> node shares [CALC]
CONS_REG = {'TAS': 8192 + 9193 + 1555 + 2224, 'FER': 5656 + 4322 + 4364, 'CEN': 5468 + 6306 + 3693,
            'STH': 5884 + 2949, 'WST': 1735 + 2204}
_tot = sum(CONS_REG.values())
NSHARE = {n: CONS_REG[n] / _tot for n in NODES}
# population 1 Jan 2026, thousands (stat.uz) [SRC]
POP_REG = {'TAS': 3178.1 + 3160.7 + 946.3 + 1566.9, 'FER': 4223.0 + 3521.8 + 3190.8,
           'CEN': 4379.8 + 1111.9 + 2107.0, 'STH': 3717.0 + 3011.0, 'WST': 2053.2 + 2069.2}
_pt = sum(POP_REG.values())
PSHARE = {n: POP_REG[n] / _pt for n in NODES}

# ---------------- scenarios: demand growth x gas supply x winter ----------------
GROWTH = {'L': (0.048, 0.5), 'H': (0.064, 0.5)}   # L: 77->123 TWh consumption 2025-35 target (Min. Energy) [CALC]; H: 2024-25 actual +6.4% [SRC]
SUPPLY = {'OFF': 0.5, 'LOW': 0.5}                  # official production forecast vs 2026 trend [ASM probabilities]
WINTER = {'N': 0.80, 'C': 0.12, 'X': 0.08}         # 5 cold Januaries in 25 yrs (Uzhydromet) -> 20% cold [CALC]; X = cold + import cut (Jan 2023, Dec 2025) [ASM split]
SCEN = {}
for (g, (gr, pg)), (sp, ps), (w, pw) in itertools.product(GROWTH.items(), SUPPLY.items(), WINTER.items()):
    SCEN[f'{g}-{sp}-{w}'] = dict(g=gr, sup=sp, w=w, p=pg * ps * pw)

# ---------------- electricity demand ----------------
D_DOM_2025 = 83.5     # TWh at busbar: 86.7 generation (Min. Energy) - 4.1 exports + 0.9 imports (Gazeta.uz; Tajik stats) [CALC]
AF_EXPORT = 2.0       # TWh/yr fixed export to Afghanistan, at STH ("over 2 TWh" 2025, Gazeta.uz) [SRC]
# daily energy relative to annual mean: winter = 283/294.4 x summer (daily records 24 Jan 2026, 18 Jul 2026);
# summer = Jul 2026 8.8 TWh / Jan-Jul mean 7.6 = 1.16; shoulder from remainder [CALC]
DAYMULT = {'W': 1.11, 'SU': 1.16}
DAYMULT['SH'] = (365 - 151 * 1.11 - 92 * 1.16) / 122
BLOCK_MULT = {'DAY': 1.02, 'PK': 1.10}             # [ASM] evening 10% above daily mean on average
BLOCK_MULT['NT'] = (24 - 9 * 1.02 - 4 * 1.10) / 11
PEAK_RATIO = 1.16          # winter record 13.2 GW / mean winter load 11.4 GW [CALC]
PEAK_2026 = 13.2           # GW winter 2025/26 peak (Min. Energy via Spot.uz) [SRC]
COLD_EL = {'N': 1.0, 'C': 1.06, 'X': 1.06}         # [ASM]
LOSS0 = 0.172              # network losses H1 2026 (Gazeta.uz, 27 Jul 2026) [SRC]
DIST_LOSS, DIST_LOSS_TARGET = 0.135, 0.081         # distribution technical loss 13-14% vs 8.1% allowed (ADB/WB) [SRC]
LOSS_PER_DIST = (DIST_LOSS - DIST_LOSS_TARGET) * 0.1 / PEAK_2026   # loss-rate cut per 0.1 GW rebuilt [CALC]

# ---------------- existing fleet (start 2027), GW by node ----------------
# Ministry of Energy end-2025: thermal 17,551 MW; GEM unit list split into classes, scaled x1.055 to the official total [CALC]
SC = 1.055
K0 = {
 'OLDG': {'TAS': 5.06 * SC, 'CEN': 1.20 * SC, 'STH': 0.80 * SC, 'WST': 0.42 * SC, 'FER': 0.28 * SC},  # Syrdarya, Tashkent, Navoi, Talimarjan, Takhiatash, Fergana steam
 'COAL': {'TAS': 2.386 * SC},                                                                       # Novo-Angren, Angren
 'CCGT': {'TAS': 1.87 * SC + 1.573, 'STH': 0.90 * SC + 1.56, 'CEN': 0.951 * SC, 'FER': 0.90 * SC, 'WST': 0.56 * SC},  # + Syrdarya-2 (Aug 2026), Surkhandarya/Angor (2027)
 'ENG':  {'TAS': 0.71 * SC, 'STH': 0.43 * SC, 'WST': 0.174 * SC},                                  # Aksa, Cenergo, Yangiariq
}
COMMITTED = {('CCGT', 'STH', 2028): 1.065}          # Talimarjan expansion under construction (GEM) [SRC]
HR = {'OLDG': 12.0, 'COAL': 11.6, 'CCGT': 6.5, 'ENG': 8.6}   # GJ/MWh: old units 25-35% eff (Concept Note); fleet 30% (JICA); CCGT 55% (Syrdarya-2 61.7%) [CALC/ASM]
GASFIRED = ['OLDG', 'CCGT', 'ENG']
AV = {'OLDG': {'W': .75, 'SH': .70, 'SU': .72}, 'COAL': {'W': .75, 'SH': .70, 'SU': .72},
      'CCGT': {'W': .90, 'SH': .85, 'SU': .88}, 'ENG': {'W': .92, 'SH': .90, 'SU': .90}}  # [ASM] no plant data published
COAL_COST = 15.0           # MUSD/TWh fuel [ASM]
CO2_GAS = 1.9              # Mt per bcm (IPCC ~56 t/TJ) [SRC]
CO2_COAL = 1.16            # Mt per TWh lignite (IPCC 101 t/TJ x 11.6 GJ/MWh) [CALC]

K_HYD0 = 2.44              # GW (Min. Energy end-2025) [SRC]
HYD_NODE = {'TAS': .65, 'FER': .15, 'CEN': .05, 'STH': .10, 'WST': .05}   # by plant location (Chirchik, Charvak...) [ASM]
E_HYD = {'W': 151 * 0.013, 'SU': 92 * 0.027}       # TWh: 13 GWh/day Jan-Feb 2026, 27 GWh/day Jul 2025 [CALC]
E_HYD['SH'] = 7.2 - E_HYD['W'] - E_HYD['SU']       # normal year 7.2 TWh = mean of 8.16 (2024) and 6.3 (2025) [CALC]
HYD_SHAPE = {s: E_HYD[s] / 7.2 for s in SEASONS}
DRY = {'N': 1.0, 'C': 6.3 / 7.2, 'X': 6.3 / 7.2}  # 2025 dry year ratio [CALC]
HYD_CF = 0.345             # Upper Pskem 484 GWh / 160 MW [CALC]
COMMITTED_HYD = {2028: 0.40}                        # Pskem 400 MW under construction [SRC]

K_SOL0 = 3.93 + 2.8 + 0.2  # GW large solar end-2025 + 2026 plan + small-scale (Min. Energy; Enerdata) [SRC]
K_WND0 = 1.652 + 0.47
K_BES0 = 1.545 + 0.884     # GW (2 h) [SRC]
SOL_NODE = {'CEN': .45, 'STH': .20, 'TAS': .20, 'FER': .05, 'WST': .10}   # by plant location [ASM]
WND_NODE = {'CEN': 1.0 / K_WND0, 'WST': 1 - 1.0 / K_WND0}               # Bash, Dzhankeldy (Bukhara) ~1 GW; rest Karakalpakstan [CALC]
# PV yield Tashkent (NASA POWER via ProfileSolar): kWh/kW/day winter 2.46, spring 6.02, autumn 4.38, summer 8.32 [SRC]
CF_SOL = {'W': (90 * 2.46 + 30 * 4.38 + 31 * 6.02) / 151 / 24, 'SH': (6.02 + 4.38) / 2 / 24, 'SU': 8.32 / 24}  # [CALC]
SOL_BLOCKSHARE = {'W': {'DAY': 1.0, 'PK': 0.0, 'NT': 0}, 'SH': {'DAY': .95, 'PK': .05, 'NT': 0},
                  'SU': {'DAY': .88, 'PK': .12, 'NT': 0}}                  # sunset 17:00 winter, 20:00 summer [ASM]
CF_WND = {'W': 0.37, 'SH': 0.36, 'SU': 0.395}      # Bash 37.7%, Dzhankeldy 35.4%, Karauzak 40% expected; Jul 2025 fleet 39.5% [CALC]
ETA_B, BESS_H = 0.85, 2.0
WIND_CREDIT = 0.15        # firm contribution at winter evening peak [ASM]
NUC = {2029: 0.055, 2030: 0.110, 2033: 1.110, 2035: 2.110}   # Jizzakh: 2x55 MW SMR 2029-30, VVER 2033, 2035 (WNN; TCA) [SRC]

# interregional links: existing capacity [ASM, not published], length [ASM, road distance]
LINKS = {'TAS-FER': ('TAS', 'FER', 2.0, 280), 'TAS-CEN': ('TAS', 'CEN', 3.0, 300),
         'CEN-STH': ('CEN', 'STH', 2.5, 200), 'CEN-WST': ('CEN', 'WST', 1.5, 450)}
CIRCUIT = 1.2              # GW per new 500 kV circuit [ASM]
LINE_COST = 0.45 * 1.3     # MUSD/km: 0.35 (EBRD Sarimay-Muruntau) to 0.55 (Surkhan-Puli Khumri), x1.3 substations [CALC/ASM]
DIST_HEADROOM = 1.05       # 2025 regional peak x 1.05 [ASM]
PEAK_2025 = 13.3           # GW (summer 21 Jul 2025) [SRC]
EIMP = {'W': 1.5, 'SH': 1.0, 'SU': 0.5}            # TWh/season power import cap [ASM]
EIMP_PK = 0.6              # GW [ASM]
EIMP_PRICE = 20.0          # MUSD/TWh: 895 GWh for USD 18.1 m from Tajikistan [CALC]
EIMP_CUT = {'N': 1.0, 'C': 1.0, 'X': 0.8}          # electricity imports fell 20% in Jan 2023 (Interfax) [SRC]

# ---------------- gas ----------------
PROD_2025 = 40.0           # bcm marketable (Energy Institute 2026 via OWID; official 42.3 gross) [SRC]
_scale = 40.0 / 42.3
OFF_PATH = {2027: 42.9, 2028: 44.5, 2029: 45.5, 2030: 48.5}  # official forecast (Kun.uz 18 Feb 2026) [SRC]
def gas_prod(t, sup):
    if sup == 'OFF':
        return _scale * OFF_PATH.get(t, 48.5)              # flat after 2030 [ASM]
    if sup == 'MID':                                       # mean of the two paths (deterministic comparison only)
        return 0.5 * (gas_prod(t, 'OFF') + gas_prod(t, 'LOW'))
    return _scale * 36.3 * 0.97 ** (t - 2026)              # 2026 implied by Jan-Aug -16% (UzDaily); -3%/yr after [CALC/ASM]
GAS_DEMAND_2025 = 44.5     # bcm (Energy Institute via OWID) [SRC]
NP_SHAPE = {'W': 0.555, 'SH': 0.255, 'SU': 0.19}   # non-power seasonal shape: 4.5 bcm/month winter vs 2.4 summer (Review.uz) minus power [CALC]
NP_2025 = 29.97            # bcm, calibrated in validate.py (= 44.5 - modelled 2025 power gas) [CALC]
G_NP = 0.02                # [ASM]
COLD_GAS = {'N': 1.0, 'C': 1.13, 'X': 1.13}        # 20 mcm/day shortfall Jan 2023 on ~150 mcm/day (Interfax; Review.uz) [CALC]
RU_CAP = {2027: 7.7}       # bcm/yr: 2025 contract ceiling 7.7 [SRC]; 11 bcm transit from 2028 [SRC plan, ASM timing]
def ru_cap(t): return RU_CAP.get(t, 11.0)
def ru_day(t): return 0.020 if t < 2030 else 0.032  # bcm/day intake 9 -> 32 mcm/d expansion (Kun.uz 2025); 2025 average 17.8 [CALC/ASM]
TM_CAP, TM_DAY = 2.0, 0.020                         # up to 2 bcm/yr (Aug 2023); 20 mcm/d (Dec 2022) [SRC]
IMP_PRICE = 160.0          # MUSD/bcm (~USD 160/1000 m3, Kommersant via Kun.uz) [SRC]
UGS0, UGS0_WD = 5.4, 0.030 # bcm working gas Gazli 4.5 + Khodzhaabad 0.9; withdrawal 30 mcm/d target [SRC]
UGS_WD_PER_BCM = 0.030 / 5.4
VOLL_E = 60.0              # MUSD/TWh = USD 0.06/kWh (World Bank 2013, Uzbekistan, "conservative") [SRC]
VOLL_G = 500.0             # MUSD/bcm [ASM ~3x import price; not published]
N_DD = {'N': 3, 'C': 10, 'X': 10}                  # design cold days per winter [ASM]
DD_NP = 1.10               # [ASM]
DD_PG = 1.05               # record day vs mean winter day 283/274 GWh [CALC]
DISC = 0.08

# ---------------- households / energy poverty ----------------
HH = 7.6                   # million households (7.6 m electricity accounts, Min. Energy 2025) [SRC]
HH_OFFGAS = 2.5            # m households on coal/firewood: "almost one third" (CABAR) x 7.6 [CALC]
HH_PER_BCM = 0.5           # million households per bcm of winter gas cut (2,000 m3 per household-winter) [CALC]
HH_PEAK_KW = 0.6           # kW household evening demand [ASM]
HH_DD_M3 = 17.0            # m3/day per household on a cold day (2,000/151 x 1.3) [CALC/ASM]

# ---------------- barter (version 3: three-leg contract from the barter design, Section 6) ----------------
# Pilot volumes per annual cycle 2027-2029; from 2030 the protocol may scale them by a factor between 1 and 2.
BARTER_KG = 0.175          # TWh Kazakh winter power to Kyrgyzstan, Nov-Mar, <=50 MW [term sheet]
BARTER_UZ = 0.075          # TWh Kazakh winter-peak power to Uzbekistan (TAS), 17:00-21:00, <=160 MW [term sheet]
BARTER_UZ_MW = 0.160       # GW
RHO = 1.35                 # GWh-eq of summer power per winter GWh (band 1.2-1.5) [term sheet]
REPAY_SPLIT = {'SU': 92 / 153, 'SH': 61 / 153}     # May-Sep window: Jun-Aug in SU, May+Sep in SH [CALC]
KG_HYDRO = 0.050           # TWh Kyrgyz summer hydro to Uzbekistan (FER), Apr-Sep, <=35 MW [term sheet]
KG_HYDRO_SPLIT = {'SU': 92 / 183, 'SH': 91 / 183}  # Apr-Sep window [CALC]
KG_WATER = 0.18            # bcm incremental Jul-Aug release to Fergana Valley canals per pilot cycle [term sheet]
WATER_VAL = 44.0           # MUSD/bcm = USD 0.044/m3 (Bekchanov et al. 2012, gross value) [SRC]
KZ_AVAIL = {'N': 1.0, 'C': 0.85, 'X': 0.70}        # share of contracted Kazakh winter power delivered [ASM]
BARTER_SCALE_MAX = 2.0     # expansion from 2030 up to twice the pilot [term sheet]
BARTER_FROM = 2030
BARTER_CAPEX = 35.0        # MUSD public, 2027: border/reservoir telemetry and settlement platform [budget line]
# Pilot blocks (<=160 MW, <=280 MW) fit inside existing cross-border capacity (~4,000 MW, CDC Energiya 2024) [SRC];
# firm-capacity works are needed only to reserve transfer capacity for a scaled-up protocol:
BARTER_EXP_CAPEX = 100.0   # MUSD public in 2029 for doubling (scale 2); pro rata for 1 < scale < 2 [budget line]
BARTER_EXP_YEAR = 2029
BARTER_ADMIN = 1.5         # MUSD/yr public, verification and settlement 2027-2036 (15 total) [budget line]
P_SUMMER, P_WINTER = 20.0, 45.0                    # MUSD/TWh: Kyrgyz sale 2 c/kWh (24.kg) [SRC]; winter value [ASM]

# ---------------- Kambarata-1 ----------------
KAMB_COST_UZ = 0.33 * 4200       # 33% share of USD 4.2 bn (range 2.9-5 bn) [SRC]
KAMB_SPEND = list(range(2027, 2033))
KAMB_ONLINE = 2033               # [ASM] first unit officially 2028; preparatory works still under way Jan 2026
KAMB_K = 0.33 * 1.86             # GW
KAMB_E = 0.33 * 5.8              # TWh/yr (5.6-6 TWh) [SRC]
KAMB_SHAPE = {'W': .50, 'SH': .25, 'SU': .25}  # [ASM] reservoir shifts output to winter

BUDGET, BUDGET_YR = 14102, 2000  # case packet Table 1 [SRC]; yearly cash cap [ASM]

# ---------------- candidate projects ----------------
# unit; capex MUSD/unit; om frac/yr; lead yrs; gmax units/yr (all nodes); pot units per node (or total); pub share; life; int; nodes
P = {
 'METH':  dict(unit='0.1 bcm/yr leaks repaired', capex=15.1, om=.05, lead=1, gmax=3, pot=10, pub=1.0, life=15, nodes=None,
   src='WB 2026: USD 10.6 m grant recovers 47,500 t/yr (~70 mcm) -> USD 151 m per bcm/yr [CALC]; potential 45% of ~2.2 bcm/yr (MethaneSAT 1.5 Mt/yr; IEA GMT 2025 Eurasia 45% no-net-cost) [CALC]'),
 'WELL':  dict(unit='10 well workovers', capex=40.6, om=0, lead=1, gmax=6, pot=30, pub=0.5, life=8, nodes=None,
   src='Uzbekneftegaz Aug 2026: 8 workovers +310,000 m3/d (39,000 m3/d/well, Trend) [SRC]; cost at Condor production cost USD 58/1000 m3 [SRC] over 8-yr output, 15%/yr decline [ASM]'),
 'UGS':   dict(unit='+0.5 bcm storage', capex=250, om=.02, lead=3, gmax=2, pot=12, pub=1.0, life=40, nodes=None, integer=True,
   src='USD 0.28/m3 (CIEP 2006) to 0.67/m3 (Thunder Said 2025) -> 0.50 [CALC]; Gazli potential 10 bcm, Qorabayir 1.5 bcm [SRC]'),
 'SOLAR': dict(unit='0.1 GW utility PV', capex=69.1, om=.015, lead=1, gmax=30, pot=400, pub=0.0, life=25, nodes=['CEN', 'STH', 'TAS'], learn=0.047,
   src='USD 691/kW (IRENA 2024); -4.7%/yr (NREL ATB 2024 moderate, -44% 2023-35) [CALC]; private IPP (16+ PPAs)'),
 'WIND':  dict(unit='0.1 GW onshore wind', capex=138, om=.025, lead=2, gmax=15, pot=150, pub=0.0, life=25, nodes=['CEN', 'WST'],
   src='Bash wind USD 1,380/kW (NS Energy) [SRC]; private IPP'),
 'BESS':  dict(unit='0.1 GW / 0.2 GWh battery', capex=33.0, om=.025, lead=1, gmax=15, pot=60, pub=0.0, life=15, nodes=NODES, learn=0.047,
   src='USD 165/kWh turnkey (BNEF 2024) [SRC]; private (Masdar, ACWA BESS)'),
 'RTSOL': dict(unit='10,000 homes: 2 kW PV + 5 kWh battery', capex=32.5, om=.01, lead=1, gmax=10, pot=10, pub=1.0, life=20, nodes=NODES,
   src='Free 1.5-2 kW panels for poor families (Gov. programme) [SRC]; USD 1,000/kW + USD 250/kWh [ASM; IRENA utility USD 758/kW lower bound]'),
 'REPW':  dict(unit='0.45 GW old steam -> CCGT', capex=450, om=.025, lead=3, gmax=2, pot=8, pub=0.0, life=30, nodes=['TAS', 'CEN', 'STH'], integer=True,
   src='Uzbek CCGT deals USD 678-1,320/kW (ACWA Sirdarya; Turakurgan) -> 1,000 [CALC]; old unit offline during build [ASM]'),
 'HYD':   dict(unit='0.1 GW hydro', capex=161, om=.01, lead=4, gmax=6, pot=15, pub=1.0, life=50, nodes=['TAS', 'STH', 'FER'],
   src='Hydro programme USD 5.8 bn for +3.6 GW 2026-32 (TCA) -> USD 1,610/kW [CALC]; CF 0.345 (Upper Pskem) [CALC]'),
 'DIST':  dict(unit='+0.1 GW distribution capacity', capex=30, om=.02, lead=2, gmax=20, pot=40, pub=1.0, life=40, nodes=NODES,
   src='WB: USD 150 m for 6,000 km LV, 1,200 transformers [SRC]; ~0.48 GVA -> USD 300/kW [CALC/ASM]'),
 'DH':    dict(unit='10,000 DH households rehabilitated', capex=25.6, om=.02, lead=2, gmax=6, pot=30, pub=1.0, life=20, nodes=None,
   src='WB DH project USD 140 m, 240,937 people, 7.5 TWh lifetime savings (~40 mcm/yr) [SRC] -> USD 2,560/household, 7.3 mcm/yr per 10k [CALC]; 1.3 m people on DH (WB 2023)'),
 'BOIL':  dict(unit='10,000 efficient gas boilers', capex=8.6, om=0, lead=1, gmax=30, pot=210, pub=0.5, life=15, nodes=None,
   src='USD 860, up to 80% efficient vs 25-50% (WB Kyrgyz study 2020) [SRC]; 55%->80% saves 31% of 2,000 m3 [CALC/ASM]'),
 'STOVE': dict(unit='10,000 clean solid-fuel stoves', capex=2.36, om=0, lead=1, gmax=40, pot=250, pub=1.0, life=10, nodes=None,
   src='USD 207 + 29 chimney, 70-87% efficient, -45-50% fuel (WB/ESMAP Kyrgyz 2020) [SRC]'),
 'INSUL': dict(unit='10,000 homes retrofitted', capex=93, om=0, lead=1, gmax=20, pot=300, pub=0.5, life=30, nodes=None,
   src='WB USD 90/m2 light retrofit x 103 m2/home (786.5 m m2 / 7.6 m) [CALC]; 25% heat saving (UNDP) [SRC]'),
 'HPUMP': dict(unit='10,000 heat pumps (gas homes)', capex=45, om=.02, lead=1, gmax=15, pot=200, pub=0.4, life=15, nodes=None,
   src='USD 3,000-6,000 (IEA 2022) -> 4,500; SCOP 2.75 (WB 2.5-3.0); 40% state subsidy (2025) [SRC/CALC]'),
 'PUMP':  dict(unit='0.1 TWh/yr pumping saved', capex=110, om=.02, lead=2, gmax=3, pot=18, pub=1.0, life=25, nodes=None,
   src='WB USD 200 m -> 165 GWh/yr; EBRD USD 250 m -> 251 GWh/yr [SRC] -> USD 1.1/kWh-yr [CALC]; potential 25% of 7.2 TWh [ASM]'),
}
WELL_GAS0, WELL_DECL = 10 * 0.039 * 365 / 1000, 0.15     # bcm/yr per 10 wells in first year
METH_GAS = 0.1
UGS_BLOCK = 0.5
DH_GAS = 0.0073; BOIL_GAS = 0.00625; INSUL_GAS = 0.005; HP_GAS = 0.020
HP_EL = 0.058                      # TWh/winter per 10k (2,000 m3 x 35.8 MJ x 0.8 / 2.75) [CALC]
HP_BLOCK = {'DAY': .30, 'PK': .25, 'NT': .45}
PUMP_SEAS = {'SH': .4, 'SU': .6}
RT_PV, RT_BATT = 0.02, 0.05e-3     # GW PV, TWh battery per day per 10k homes
SEC = ['TAS-FER', 'TAS-CEN', 'CEN-STH', 'CEN-WST']
MUSTRUN_OLD_W = 0.5        # winter must-run share of old units (CHP heat duty) [ASM, calibrated in 2025 back-cast]
# ---------------- gas curtailment order, phased reliability rule, Russian import cut ----------------
IND_SHARE = 0.32           # industry 12% + transport (CNG) 8% of 2020 gas demand / non-power share 62% (IEA 2022 review) [CALC]
VOLL_GI = 250.0            # MUSD/bcm, industrial/CNG curtailment, cut first (CNG stations closed Jan 2023, Eurasianet) [ASM value]
RU_CUT_X = 0.006           # bcm/day Russian import cut in winter X (Dec 2025 ~6 mcm/day, Trend) [SRC]
EENS_PHASE = [(2027, 2029, 0.025), (2030, 2036, 0.0044)]  # ~2 TWh curtailed winter 2022 / 81.5 TWh [CALC]; 2024 level 357 GWh [SRC]

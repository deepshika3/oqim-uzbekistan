# OQIM: Warm Homes and Firm Winter Evenings

Planning model and paper source for Team 462's Round 2 plan in the Switch 2026 Global Competition: a ten-year plan (2027–2036) for reliable winter energy in Uzbekistan.

## What is here

| Folder | Contents |
|---|---|
| `model/` | Two-stage stochastic planning model of Uzbekistan's power and gas system (Pyomo + HiGHS), the scripts behind every number in the paper, and their saved results (`*.json`). |
| `paper/` | LaTeX source of the paper (`main.tex`, `refs.bib`, `figures/`). Compiles with pdfLaTeX, e.g. in Overleaf. |

## The model in brief

Stage 1 chooses what to build, where and when in 2027–2036 (16 project types, 500 kV circuits, a Kambarata-1 share and the size of the seasonal barter). Stage 2 runs the system in each of 12 futures (two demand paths × two gas paths × three winters) across five regions, three seasons, three parts of the day and a cold design day. It minimises expected present cost over 2027–2040 at 8%, within the US$14.1 billion public budget (at most US$2.0 billion a year), with two service limits in expectation: unserved electricity below 2.5% (2027–2029) and 0.44% (from 2030) of demand, and at most 1.5 million households in winter energy poverty from 2030.

Every input in `model/data2.py` is tagged in a comment as `[SRC]` (sourced), `[CALC]` (calculated from sourced values) or `[ASM]` (assumption).

## Files in `model/`

| File | What it does | Output |
|---|---|---|
| `data2.py` | All inputs, with sources | |
| `model2.py` | Builds (`build`) and solves (`solve`) the model | |
| `validate.py` | Back-cast of 2025 against actual statistics | `validation.json` |
| `runall.py` | Plan, no new projects, cost only, risk-averse, deterministic and wait-and-see runs, delay tests | `results3.json`, `stage1_v3.json` |
| `sens2.py` | Sensitivities (gas path, availability, lines, value of unserved gas, discount rate) | `sens3.json` |
| `frontier2.py` | Cost of tighter caps on households in energy poverty | `frontier3.json` |
| `evcheck3.py` | Average-future plan tested in all futures | `evcheck3.json` |
| `extra3.py` | Commissioning-delay tests | `extra3.json` |
| `barterval.py` | Value of the seasonal barter to Uzbekistan | `barterval.json` |
| `strict3.py` | Stricter targets (≤1.0 m households from 2032, cuts <0.2%), used for the conditional tranche | `strict3.json` |
| `bess_sweep.py` | Battery cost at which storage enters the plan | `bess_sweep.json` |
| `extract3.py` | Collects the numbers quoted in the paper | `paper_numbers.json` |

## How to run

```bash
cd model
pip install -r requirements.txt
python validate.py     # about 1 s
python runall.py       # about 10 min
python sens2.py        # about 5 min
python frontier2.py    # about 5 min
python evcheck3.py
python extra3.py
python barterval.py
python strict3.py
python bess_sweep.py   # about 2 min
python extract3.py
```

The model has about 78,700 variables and solves to a 0.5% optimality gap in under a minute per run.

## Key results (expected over the 12 futures)

- Households in winter energy poverty: at most 1.5 million from 2030, against 5.7 million by 2036 with no new projects.
- Public cost of the model's portfolio: US$5.0 billion; present-value saving against doing nothing: US$2.1 billion (2027–2040).
- Gas imports 9.7 bcm lower and industrial gas cuts 15 bcm lower over 2027–2036.
- Main builds: 1.0 bcm/yr of leak repair, 300 well workovers, 9.4 GW of distribution upgrades, one Tashkent–Fergana 500 kV circuit, 2.1 million efficient boilers, 1.18 million clean stoves and 11 GW of privately financed solar.

## Citation

Team 462. *OQIM: Warm Homes and Firm Winter Evenings — Round 2 planning model and paper*, Switch 2026 Global Competition, 2026.

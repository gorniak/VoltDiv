# VoltDiv — Feedback Voltage Divider Optimizer

Find optimal standard resistor values (`E24`, `E48`, `E96`, `E192`, `E24+E48`, `E24+E96`, or a custom BOM list) for the feedback voltage divider of a voltage regulator or DC-DC converter.

**Live web app:** [https://gorniak.eu/calc/voltdiv/](https://gorniak.eu/calc/voltdiv/)

## Supported Topologies

| Mode | Topology | Equation | Search Algorithm |
|------|----------|----------|------------------|
| `TB` | **T + B** (Top + Bottom) | $V_{\text{OUT}} = V_{\text{REF}} \left(1 + \frac{R_T}{R_B}\right)$ | $O(N \log N)$ binary search |
| `T1T2B` | **T1 + T2 + B** (2 Top in series + Bottom) | $V_{\text{OUT}} = V_{\text{REF}} \left(1 + \frac{R_{T1} + R_{T2}}{R_B}\right)$ | $O(N^2)$ monotonic two-pointer scan |
| `TB1B2` | **T + B1 \|\| B2** (Top + 2 Bottom parallel) | $V_{\text{OUT}} = V_{\text{REF}} \left(1 + \frac{R_T}{R_{B1} \parallel R_{B2}}\right)$ | $O(N^2)$ conductance two-pointer scan |

## Available Implementations

The same optimization engine is provided in three forms:

| File | Runs in | Use it for |
|------|---------|------------|
| `voltdiv.html` | Any browser (single standalone file, zero dependencies) | Interactive design, schematics, sorting, shareable links, CSV export |
| `voltdiv.py` | Python 3 (standard library only) | CLI, scripts, batch automation, AI agents |
| `voltdiv.ts` / `voltdiv.js` | Node.js / TypeScript | CLI, JS/TS projects, web integration |
| `old_version/voltdiv.py` | Python 3 | Original 2022 script kept for reference |

## Web App (`voltdiv.html`)

Open `voltdiv.html` directly in any browser or visit [https://gorniak.eu/calc/voltdiv/](https://gorniak.eu/calc/voltdiv/).

- Switch between `T + B`, `T1 + T2 + B`, and `T + B1 || B2` with live IEC/KiCad-style schematics and equations.
- Click any row in the results table to preview those resistor values on the schematic.
- Supports engineering suffixes (`1k`, `100k`, `4R7`, `2k2`, `1.5M`), sortable columns, shareable query-parameter URLs, and CSV export (`voltdiv_YYYY-MM-DD_HHMMSS.csv`).

## Python (`voltdiv.py`)

No external packages required (Python 3 standard library only):

```sh
python3 voltdiv.py --vout 1.1 --vref 0.6 --mode TB --series E24_E96
python3 voltdiv.py --vout 3.3 --vref 0.8 --mode T1T2B --series E96 --rmin 1k --rmax 100k
python3 voltdiv.py --vout 1.1 --vref 0.6 --mode TB1B2 --csv
python3 voltdiv.py --vout 5.0 --vref 1.25 --custom "1k,2.2k,4.7k,10k,22k,47k" --json
```

Importable API:

```python
from voltdiv import optimize_divider

results = optimize_divider(vout=3.3, vref=0.8, mode="TB", series="E96", r_min=1e3, r_max=100e3)
best = results[0]
print(best.r1, best.r2, best.vout, best.err_v)
```

## TypeScript / JavaScript (`voltdiv.ts` / `voltdiv.js`)

Run directly with Node.js:

```sh
node voltdiv.js --vout 1.1 --vref 0.6 --mode TB --series E24_E96
node voltdiv.js --vout 3.3 --vref 0.8 --mode TB1B2 --series E96 --json
```

Compile from TypeScript:

```sh
tsc voltdiv.ts --target ES2020 --module commonjs
```

Importable API:

```ts
import { optimizeDivider } from "./voltdiv";

const results = optimizeDivider({ vout: 3.3, vref: 0.8, mode: "TB", series: "E96" });
console.log(results[0]);
```

## CLI Options (`voltdiv.py` & `voltdiv.js`)

| Option | Default | Description |
|--------|---------|-------------|
| `--vout VAL` | `1.1` | Required output voltage (V) |
| `--vref VAL` | `0.6` | Reference voltage (V) |
| `--mode MODE` | `TB` | Topology: `TB`, `T1T2B`, or `TB1B2` |
| `--series SER` | `E24_E96` | `E24`, `E48`, `E96`, `E24_E48`, `E24_E96`, `E192` |
| `--custom LIST` | — | Comma/space separated custom resistor values |
| `--rmin VAL` | `1k` | Minimum resistance |
| `--rmax VAL` | `100k` | Maximum resistance |
| `--max-err VAL` | `0.1` | Maximum output voltage error (V) |
| `--top N` | `20` | Number of rows to display (`0` = all) |
| `--csv [FILE]` | — | Export CSV (default: `voltdiv_YYYY-MM-DD_HHMMSS.csv`) |
| `--sep CHAR` | `;` | CSV column separator |
| `--decimal CHAR` | `.` | CSV decimal separator |
| `--json` | — | Output results as JSON |

## For AI Agents

See [SKILL.md](SKILL.md) for agent-ready instructions and CLI examples.

## Legacy Version

The original 2022 script (configured by editing constants at the top of the file) is preserved in `old_version/voltdiv.py`.

## License

[MIT License](LICENSE), Copyright (c) 2023-2026 Radosław Górniak.
---
name: voltdiv-optimizer
description: Find optimal standard resistor values (E24, E48, E96, E192, or custom) for a feedback voltage divider of a DC-DC converter or linear regulator in T+B, T1+T2+B (2 top in series), and T+(B1||B2) (2 bottom in parallel) topologies using voltdiv.py or voltdiv.js.
---

# Feedback Voltage Divider Optimizer (`VoltDiv`)

This directory provides the same voltage divider optimization engine as a standalone web app (`voltdiv.html`), a zero-dependency Python 3 CLI/module (`voltdiv.py`), and a TypeScript/JavaScript CLI/module (`voltdiv.ts` / `voltdiv.js`).

## Topologies

| Mode    | Label         | Equation                                                      | Algorithm |
|---------|---------------|---------------------------------------------------------------|-----------|
| `TB`    | `T+B`         | $V_{\text{OUT}} = V_{\text{REF}} (1 + R_T / R_B)$             | $O(N \log N)$ binary search |
| `T1T2B` | `T1+T2+B`     | $V_{\text{OUT}} = V_{\text{REF}} (1 + (R_{T1} + R_{T2}) / R_B)$ | $O(N^2)$ two-pointer scan |
| `TB1B2` | `T+(B1\|\|B2)` | $V_{\text{OUT}} = V_{\text{REF}} (1 + R_T / (R_{B1} \parallel R_{B2}))$ | $O(N^2)$ conductance two-pointer scan |

## Usage

### Python (`voltdiv.py`, no dependencies)

```sh
python3 voltdiv.py --vout 3.3 --vref 0.8 --mode TB --series E96 --rmin 1k --rmax 100k
python3 voltdiv.py --vout 1.1 --vref 0.6 --mode T1T2B --series E24_E96 --top 10
python3 voltdiv.py --vout 1.1 --vref 0.6 --mode TB1B2 --series E24 --csv
python3 voltdiv.py --vout 5.0 --vref 1.25 --custom "1k,2.2k,4.7k,10k,22k,47k" --json
```

### Node.js (`voltdiv.js`)

```sh
node voltdiv.js --vout 3.3 --vref 0.8 --mode TB --series E96 --rmin 1k --rmax 100k
node voltdiv.js --vout 1.1 --vref 0.6 --mode TB1B2 --series E24_E96 --json
```

### Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--vout VAL` | `1.1` | Required output voltage in V |
| `--vref VAL` | `0.6` | Feedback reference voltage in V (must be `< vout`) |
| `--mode MODE` | `TB` | `TB`, `T1T2B`, or `TB1B2` |
| `--series SER` | `E24_E96` | `E24`, `E48`, `E96`, `E24_E48`, `E24_E96`, `E192` |
| `--custom LIST` | — | Comma/space separated custom resistor values (overrides `--series`, `--rmin`, `--rmax`) |
| `--rmin VAL` | `1k` | Minimum resistance (supports `R`, `k`, `M`, `4R7`, `2k2`) |
| `--rmax VAL` | `100k` | Maximum resistance |
| `--max-err VAL` | `0.1` | Maximum allowed output voltage error in V |
| `--top N` | `20` | Number of rows printed (`0` = all) |
| `--csv [FILE]` | — | Export all matches to CSV (default name: `voltdiv_YYYY-MM-DD_HHMMSS.csv`) |
| `--sep CHAR` | `;` | CSV column separator |
| `--decimal CHAR` | `.` | CSV decimal point |
| `--json` | — | Print structured JSON output (recommended for AI agents) |

## Recommended Workflow for Agents

1. Start with `--mode TB --series E96 --json --top 10` (or the user's preferred series and resistance range).
2. If the best `TB` error exceeds the user's tolerance, also run `--mode T1T2B` (2 top resistors in series) and `--mode TB1B2` (2 bottom resistors in parallel) and compare the lowest-error options alongside divider current (`current_ua`) and power dissipation (`power_mw`).
3. Report the recommended resistor values, resulting $V_{\text{OUT}}$, voltage error in mV and %, and divider current in µA.

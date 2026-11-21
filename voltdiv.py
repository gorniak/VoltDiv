#!/usr/bin/env python3
"""
Feedback Voltage Divider Optimizer (voltdiv.py)

Find optimal standard resistor values (E24, E48, E96, E192, or custom) for a
voltage regulator feedback divider in three topologies:
  - TB     : T + B           (1 top resistor, 1 bottom resistor)
  - T1T2B  : T1 + T2 + B     (2 top resistors in series, 1 bottom resistor)
  - TB1B2  : T + (B1 || B2)  (1 top resistor, 2 bottom resistors in parallel)

Author: Radoslaw Gorniak
License: MIT License
"""

from __future__ import annotations

import argparse
import bisect
import datetime
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence

SERIES_DATA: Dict[str, List[int]] = {
    "E24": [
        100, 110, 120, 130, 150, 160, 180, 200, 220, 240, 270, 300,
        330, 360, 390, 430, 470, 510, 560, 620, 680, 750, 820, 910,
    ],
    "E48": [
        100, 105, 110, 115, 121, 127, 133, 140, 147, 154, 162, 169,
        178, 187, 196, 205, 215, 226, 237, 249, 261, 274, 287, 301,
        316, 332, 348, 365, 383, 402, 422, 442, 464, 487, 511, 536,
        562, 590, 619, 649, 681, 715, 750, 787, 825, 866, 909, 953,
    ],
    "E96": [
        100, 102, 105, 107, 110, 113, 115, 118, 121, 124, 127, 130,
        133, 137, 140, 143, 147, 150, 154, 158, 162, 165, 169, 174,
        178, 182, 187, 191, 196, 200, 205, 210, 215, 221, 226, 232,
        237, 243, 249, 255, 261, 267, 274, 280, 287, 294, 301, 309,
        316, 324, 332, 340, 348, 357, 365, 374, 383, 392, 402, 412,
        422, 432, 442, 453, 464, 475, 487, 499, 511, 523, 536, 549,
        562, 576, 590, 604, 619, 634, 649, 665, 681, 698, 715, 732,
        750, 768, 787, 806, 825, 845, 866, 887, 909, 931, 953, 976,
    ],
    "E192": [
        100, 101, 102, 104, 105, 106, 107, 109, 110, 111, 113, 114,
        115, 117, 118, 120, 121, 123, 124, 126, 127, 129, 130, 132,
        133, 135, 137, 138, 140, 142, 143, 145, 147, 149, 150, 152,
        154, 156, 158, 160, 162, 164, 165, 167, 169, 172, 174, 176,
        178, 180, 182, 184, 187, 189, 191, 193, 196, 198, 200, 203,
        205, 208, 210, 213, 215, 218, 221, 223, 226, 229, 232, 234,
        237, 240, 243, 246, 249, 252, 255, 258, 261, 264, 267, 271,
        274, 277, 280, 284, 287, 291, 294, 298, 301, 305, 309, 312,
        316, 320, 324, 328, 332, 336, 340, 344, 348, 352, 357, 361,
        365, 370, 374, 379, 383, 388, 392, 397, 402, 407, 412, 417,
        422, 427, 432, 437, 442, 448, 453, 459, 464, 470, 475, 481,
        487, 493, 499, 505, 511, 517, 523, 530, 536, 542, 549, 556,
        562, 569, 576, 583, 590, 597, 604, 612, 619, 626, 634, 642,
        649, 657, 665, 673, 681, 690, 698, 706, 715, 723, 732, 741,
        750, 759, 768, 777, 787, 796, 806, 816, 825, 835, 845, 856,
        866, 876, 887, 898, 909, 920, 931, 942, 953, 965, 976, 988,
    ],
}

TOPOLOGY_LABELS: Dict[str, str] = {
    "TB": "T+B",
    "T1T2B": "T1+T2+B",
    "TB1B2": "T+(B1||B2)",
}


@dataclass
class DividerResult:
    mode: str
    r1: float
    r2: float
    r3: Optional[float]
    r_top_eq: float
    r_bot_eq: float
    r_total: float
    vout: float
    err_v: float
    abs_err: float
    err_pct: float
    current_ua: float
    power_mw: float


def parse_eng_value(text: str) -> float:
    """Parse engineering notation such as '1.1', '10k', '4R7', '2k2', '1.5M', '100m'."""
    s = re.sub(r"(?i)ohms?|Ω", "", str(text).strip().replace(",", ".")).strip()
    if not s:
        raise ValueError(f"Invalid empty value: {text!r}")

    eu_match = re.match(r"^(\d+)([rRkKmMgG])(\d+)$", s)
    if eu_match:
        num = float(f"{eu_match.group(1)}.{eu_match.group(3)}")
        suf = eu_match.group(2)
        scale = {"r": 1.0, "R": 1.0, "k": 1e3, "K": 1e3, "m": 1e-3, "M": 1e6, "g": 1e9, "G": 1e9}
        return num * scale[suf]

    match = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Zµμ]*)$", s)
    if not match:
        raise ValueError(f"Cannot parse engineering value: {text!r}")

    num = float(match.group(1))
    suf = match.group(2)
    if not suf or suf in ("r", "R"):
        return num
    if suf in ("k", "K"):
        return num * 1e3
    if suf == "M" or suf.lower() == "meg":
        return num * 1e6
    if suf in ("g", "G"):
        return num * 1e9
    if suf == "m":
        return num * 1e-3
    if suf in ("u", "µ", "μ"):
        return num * 1e-6
    if suf == "n":
        return num * 1e-9
    if suf == "p":
        return num * 1e-12
    raise ValueError(f"Unknown SI suffix {suf!r} in {text!r}")


def format_resistance(ohms: float) -> str:
    if ohms >= 1e6:
        return f"{ohms / 1e6:.4g} MΩ"
    if ohms >= 1e3:
        return f"{ohms / 1e3:.4g} kΩ"
    return f"{ohms:.4g} Ω"


def get_series_base(series: str) -> List[int]:
    key = series.upper().replace("+", "_")
    if key == "E24_E48":
        return sorted(set(SERIES_DATA["E24"]) | set(SERIES_DATA["E48"]))
    if key == "E24_E96":
        return sorted(set(SERIES_DATA["E24"]) | set(SERIES_DATA["E96"]))
    if key in SERIES_DATA:
        return list(SERIES_DATA[key])
    raise ValueError(f"Unknown resistor series: {series!r}. Choose from E24, E48, E96, E24_E48, E24_E96, E192.")


def get_candidate_resistors(
    series: str = "E24_E96",
    r_min: float = 1000.0,
    r_max: float = 100000.0,
    custom_values: Optional[Sequence[float]] = None,
) -> List[float]:
    if custom_values is not None:
        cleaned = sorted({float(f"{v:.6g}") for v in custom_values if v > 0})
        return cleaned

    if r_min <= 0 or r_max < r_min:
        raise ValueError("Resistance bounds must satisfy 0 < r_min <= r_max.")

    base = get_series_base(series)
    min_dec = max(-4, int(math.floor(math.log10(r_min))) - 2)
    max_dec = min(7, int(math.ceil(math.log10(r_max))))
    values = set()
    for exp in range(min_dec, max_dec + 1):
        mult = 10.0 ** exp
        for b in base:
            r = float(f"{b * mult:.6g}")
            if r_min * (1.0 - 1e-9) <= r <= r_max * (1.0 + 1e-9):
                values.add(r)
    return sorted(values)


def _build_result(
    mode: str,
    r1: float,
    r2: float,
    r3: Optional[float],
    r_top_eq: float,
    r_bot_eq: float,
    vref: float,
    vout_target: float,
) -> DividerResult:
    vout_actual = vref * (1.0 + r_top_eq / r_bot_eq)
    err_v = vout_actual - vout_target
    abs_err = abs(err_v)
    err_pct = (err_v / vout_target) * 100.0
    r_total = r_top_eq + r_bot_eq
    current_ua = (vout_actual / r_total) * 1e6
    power_mw = ((vout_actual * vout_actual) / r_total) * 1e3
    return DividerResult(
        mode=mode,
        r1=r1,
        r2=r2,
        r3=r3,
        r_top_eq=r_top_eq,
        r_bot_eq=r_bot_eq,
        r_total=r_total,
        vout=vout_actual,
        err_v=err_v,
        abs_err=abs_err,
        err_pct=err_pct,
        current_ua=current_ua,
        power_mw=power_mw,
    )


def solve_tb(values: Sequence[float], vout_target: float, vref: float, max_err: float) -> List[DividerResult]:
    """O(N log N) binary search for T + B topology."""
    ratio = vout_target / vref - 1.0
    n = len(values)
    results: List[DividerResult] = []
    seen = set()

    for r_b in values:
        r_t_ideal = r_b * ratio
        idx = bisect.bisect_left(values, r_t_ideal)
        for ci in (idx, idx - 1):
            if 0 <= ci < n:
                r_t = values[ci]
                key = (r_t, r_b)
                if key in seen:
                    continue
                seen.add(key)
                row = _build_result("TB", r_t, r_b, None, r_t, r_b, vref, vout_target)
                if row.abs_err <= max_err + 1e-12:
                    results.append(row)
    return results


def solve_t1t2b(values: Sequence[float], vout_target: float, vref: float, max_err: float) -> List[DividerResult]:
    """O(N^2) monotonic two-pointer scan for T1 + T2 + B (2 top resistors in series)."""
    ratio = vout_target / vref - 1.0
    n = len(values)
    results: List[DividerResult] = []
    seen = set()

    for r_b in values:
        target_sum = r_b * ratio
        right = n - 1
        for left in range(n):
            r1 = values[left]
            while right > left and r1 + values[right] > target_sum:
                right -= 1
            for idx2 in (right, right + 1):
                if left <= idx2 < n:
                    r2 = values[idx2]
                    key = (r1, r2, r_b)
                    if key in seen:
                        continue
                    seen.add(key)
                    row = _build_result("T1T2B", r1, r2, r_b, r1 + r2, r_b, vref, vout_target)
                    if row.abs_err <= max_err + 1e-12:
                        results.append(row)
            if r1 > target_sum and right == left:
                break
    return results


def solve_tb1b2(values: Sequence[float], vout_target: float, vref: float, max_err: float) -> List[DividerResult]:
    """O(N^2) conductance-domain two-pointer scan for T + (B1 || B2) (2 bottom resistors in parallel)."""
    ratio = vout_target / vref - 1.0
    n = len(values)
    r_desc = list(reversed(values))
    g_asc = [1.0 / r for r in r_desc]
    results: List[DividerResult] = []
    seen = set()

    for r_t in values:
        g_target = ratio / r_t
        right = n - 1
        for left in range(n):
            g1 = g_asc[left]
            while right > left and g1 + g_asc[right] > g_target:
                right -= 1
            for idx2 in (right, right + 1):
                if left <= idx2 < n:
                    r_a = r_desc[left]
                    r_b = r_desc[idx2]
                    r_b1, r_b2 = (r_a, r_b) if r_a <= r_b else (r_b, r_a)
                    key = (r_t, r_b1, r_b2)
                    if key in seen:
                        continue
                    seen.add(key)
                    r_bot_eq = (r_b1 * r_b2) / (r_b1 + r_b2)
                    row = _build_result("TB1B2", r_t, r_b1, r_b2, r_t, r_bot_eq, vref, vout_target)
                    if row.abs_err <= max_err + 1e-12:
                        results.append(row)
            if g1 > g_target and right == left:
                break
    return results


def optimize_divider(
    vout: float,
    vref: float,
    mode: str = "TB",
    series: str = "E24_E96",
    r_min: float = 1000.0,
    r_max: float = 100000.0,
    max_err: float = 0.1,
    custom_values: Optional[Sequence[float]] = None,
) -> List[DividerResult]:
    """Find and sort optimal resistor combinations for the requested topology."""
    if vout <= 0 or vref <= 0:
        raise ValueError("vout and vref must be positive.")
    if vout <= vref:
        raise ValueError("vout must be strictly greater than vref.")
    if max_err < 0:
        raise ValueError("max_err must be >= 0.")

    mode_key = mode.upper().replace(" ", "").replace("+", "").replace("||", "").replace("(", "").replace(")", "")
    if mode_key not in ("TB", "T1T2B", "TB1B2"):
        raise ValueError(f"Unknown mode {mode!r}. Choose TB, T1T2B, or TB1B2.")

    candidates = get_candidate_resistors(series=series, r_min=r_min, r_max=r_max, custom_values=custom_values)
    if not candidates:
        return []

    if mode_key == "TB":
        results = solve_tb(candidates, vout, vref, max_err)
    elif mode_key == "T1T2B":
        results = solve_t1t2b(candidates, vout, vref, max_err)
    else:
        results = solve_tb1b2(candidates, vout, vref, max_err)

    results.sort(key=lambda r: (r.abs_err, r.r_total))
    return results


def write_csv(
    path: str,
    results: Sequence[DividerResult],
    vout: float,
    vref: float,
    mode: str,
    sep: str = ";",
    decimal: str = ".",
) -> None:
    def fmt(val: float, decimals: int) -> str:
        s = f"{val:.{decimals}f}"
        return s.replace(".", decimal) if decimal != "." else s

    lines = [
        f"Required output voltage{sep}{sep}{str(vout).replace('.', decimal)}{sep}V",
        f"Reference voltage{sep}{sep}{str(vref).replace('.', decimal)}{sep}V",
        f"Topology{sep}{sep}{TOPOLOGY_LABELS[mode]}{sep}",
        "",
    ]

    if mode == "TB":
        lines.append(sep.join(["R_TOP [Ohm]", "R_BOT [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"]))
        for r in results:
            lines.append(sep.join([
                str(r.r1).replace(".", decimal),
                str(r.r2).replace(".", decimal),
                fmt(r.vout, 4), fmt(r.err_v, 4), fmt(r.err_pct, 4),
                fmt(r.current_ua, 2), fmt(r.power_mw, 3),
            ]))
    elif mode == "T1T2B":
        lines.append(sep.join(["R_TOP1 [Ohm]", "R_TOP2 [Ohm]", "R_BOT [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"]))
        for r in results:
            lines.append(sep.join([
                str(r.r1).replace(".", decimal),
                str(r.r2).replace(".", decimal),
                str(r.r3).replace(".", decimal),
                fmt(r.vout, 4), fmt(r.err_v, 4), fmt(r.err_pct, 4),
                fmt(r.current_ua, 2), fmt(r.power_mw, 3),
            ]))
    else:
        lines.append(sep.join(["R_TOP [Ohm]", "R_BOT1 [Ohm]", "R_BOT2 [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"]))
        for r in results:
            lines.append(sep.join([
                str(r.r1).replace(".", decimal),
                str(r.r2).replace(".", decimal),
                str(r.r3).replace(".", decimal),
                fmt(r.vout, 4), fmt(r.err_v, 4), fmt(r.err_pct, 4),
                fmt(r.current_ua, 2), fmt(r.power_mw, 3),
            ]))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _print_table(results: Sequence[DividerResult], mode: str, top: int) -> None:
    shown = results[:top] if top > 0 else results
    if mode == "TB":
        headers = ["#", "R_T", "R_B", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"]
    elif mode == "T1T2B":
        headers = ["#", "R_T1", "R_T2", "R_B", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"]
    else:
        headers = ["#", "R_T", "R_B1", "R_B2", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"]

    rows = []
    for idx, r in enumerate(shown, 1):
        err_mv = r.err_v * 1000.0
        err_mv_str = "0" if abs(err_mv) < 0.005 else f"{err_mv:+.2f}"
        err_pct_str = "0%" if abs(r.err_pct) < 0.0005 else f"{r.err_pct:+.3f}%"
        if mode == "TB":
            r_cols = [format_resistance(r.r1), format_resistance(r.r2)]
        else:
            r_cols = [format_resistance(r.r1), format_resistance(r.r2), format_resistance(r.r3 or 0.0)]
        rows.append([
            str(idx), *r_cols, f"{r.vout:.4f}", err_mv_str, err_pct_str, f"{r.current_ua:.2f}", f"{r.power_mw:.3f}"
        ])

    widths = [max(len(h), *(len(row[i]) for row in rows)) if rows else len(h) for i, h in enumerate(headers)]
    print("  ".join(h.rjust(w) for h, w in zip(headers, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(c.rjust(w) for c, w in zip(row, widths)))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Feedback Voltage Divider Optimizer (T+B, T1+T2+B, T+(B1||B2))"
    )
    parser.add_argument("--vout", default="1.1", help="Required output voltage in V (default: 1.1)")
    parser.add_argument("--vref", default="0.6", help="Feedback reference voltage in V (default: 0.6)")
    parser.add_argument(
        "--mode",
        default="TB",
        help="Topology: TB (T+B), T1T2B (T1+T2+B), TB1B2 (T+(B1||B2)) (default: TB)",
    )
    parser.add_argument(
        "--series",
        default="E24_E96",
        help="Resistor series: E24, E48, E96, E24_E48, E24_E96, E192 (default: E24_E96)",
    )
    parser.add_argument("--custom", help="Comma/space separated custom resistor list (e.g. '1k,2.2k,4.7k,10k')")
    parser.add_argument("--rmin", default="1k", help="Minimum resistance (default: 1k)")
    parser.add_argument("--rmax", default="100k", help="Maximum resistance (default: 100k)")
    parser.add_argument("--max-err", default="0.1", help="Max output voltage error in V (default: 0.1)")
    parser.add_argument("--top", type=int, default=20, help="Number of results to print (0 = all, default: 20)")
    parser.add_argument("--csv", nargs="?", const="AUTO", help="Export results to CSV (optional path; default: voltdiv_YYYY-MM-DD_HHMMSS.csv)")
    parser.add_argument("--sep", default=";", help="CSV column separator (default: ';')")
    parser.add_argument("--decimal", default=".", help="CSV decimal separator (default: '.')")
    parser.add_argument("--json", action="store_true", help="Output top results as JSON")

    args = parser.parse_args(argv)

    try:
        vout = parse_eng_value(args.vout)
        vref = parse_eng_value(args.vref)
        r_min = parse_eng_value(args.rmin)
        r_max = parse_eng_value(args.rmax)
        max_err = parse_eng_value(args.max_err)
        custom_vals = (
            [parse_eng_value(tok) for tok in re.split(r"[\s,;]+", args.custom.strip()) if tok]
            if args.custom
            else None
        )
        mode_key = args.mode.upper().replace(" ", "").replace("+", "").replace("||", "").replace("(", "").replace(")", "")
        results = optimize_divider(
            vout=vout,
            vref=vref,
            mode=mode_key,
            series=args.series,
            r_min=r_min,
            r_max=r_max,
            max_err=max_err,
            custom_values=custom_vals,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.csv:
        if args.csv == "AUTO":
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            csv_path = f"voltdiv_{ts}.csv"
        else:
            csv_path = args.csv
        write_csv(csv_path, results, vout, vref, mode_key, sep=args.sep, decimal=args.decimal)
        if not args.json:
            print(f"Saved {len(results)} results to {csv_path}")

    if args.json:
        shown = results[: args.top] if args.top > 0 else results
        print(json.dumps({
            "vout": vout,
            "vref": vref,
            "mode": mode_key,
            "topology": TOPOLOGY_LABELS[mode_key],
            "total_matches": len(results),
            "results": [asdict(r) for r in shown],
        }, indent=2))
        return 0

    print(f"V_OUT = {vout} V | V_REF = {vref} V | Topology = {TOPOLOGY_LABELS[mode_key]} | Matches = {len(results)}")
    if not results:
        print("No matching resistor combinations found within the specified constraints.")
        return 0
    print()
    _print_table(results, mode_key, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

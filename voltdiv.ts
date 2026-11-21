#!/usr/bin/env node
/**
 * Feedback Voltage Divider Optimizer (voltdiv.ts)
 *
 * Find optimal standard resistor values (E24, E48, E96, E192, or custom) for a
 * voltage regulator feedback divider in three topologies:
 *   - TB     : T + B           (1 top resistor, 1 bottom resistor)
 *   - T1T2B  : T1 + T2 + B     (2 top resistors in series, 1 bottom resistor)
 *   - TB1B2  : T + (B1 || B2)  (1 top resistor, 2 bottom resistors in parallel)
 *
 * Author: Radoslaw Gorniak
 * License: MIT License
 */

export type TopologyMode = "TB" | "T1T2B" | "TB1B2";
export type SeriesKey = "E24" | "E48" | "E96" | "E24_E48" | "E24_E96" | "E192";

export interface DividerResult {
    mode: TopologyMode;
    r1: number;
    r2: number;
    r3: number | null;
    rTopEq: number;
    rBotEq: number;
    rTotal: number;
    vout: number;
    errV: number;
    absErr: number;
    errPct: number;
    currentUa: number;
    powerMw: number;
}

export interface OptimizeOptions {
    vout: number;
    vref: number;
    mode?: TopologyMode | string;
    series?: SeriesKey | string;
    rMin?: number;
    rMax?: number;
    maxErr?: number;
    customValues?: number[];
}

export const SERIES_DATA: Record<"E24" | "E48" | "E96" | "E192", number[]> = {
    E24: [
        100, 110, 120, 130, 150, 160, 180, 200, 220, 240, 270, 300,
        330, 360, 390, 430, 470, 510, 560, 620, 680, 750, 820, 910,
    ],
    E48: [
        100, 105, 110, 115, 121, 127, 133, 140, 147, 154, 162, 169,
        178, 187, 196, 205, 215, 226, 237, 249, 261, 274, 287, 301,
        316, 332, 348, 365, 383, 402, 422, 442, 464, 487, 511, 536,
        562, 590, 619, 649, 681, 715, 750, 787, 825, 866, 909, 953,
    ],
    E96: [
        100, 102, 105, 107, 110, 113, 115, 118, 121, 124, 127, 130,
        133, 137, 140, 143, 147, 150, 154, 158, 162, 165, 169, 174,
        178, 182, 187, 191, 196, 200, 205, 210, 215, 221, 226, 232,
        237, 243, 249, 255, 261, 267, 274, 280, 287, 294, 301, 309,
        316, 324, 332, 340, 348, 357, 365, 374, 383, 392, 402, 412,
        422, 432, 442, 453, 464, 475, 487, 499, 511, 523, 536, 549,
        562, 576, 590, 604, 619, 634, 649, 665, 681, 698, 715, 732,
        750, 768, 787, 806, 825, 845, 866, 887, 909, 931, 953, 976,
    ],
    E192: [
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
};

export const TOPOLOGY_LABELS: Record<TopologyMode, string> = {
    TB: "T+B",
    T1T2B: "T1+T2+B",
    TB1B2: "T+(B1||B2)",
};

export function parseEngValue(str: string): number {
    const s = str.trim().replace(",", ".").replace(/Ω|ohms?/gi, "").trim();
    if (!s) return NaN;

    const euMatch = s.match(/^(\d+)([rRkKmMgG])(\d+)$/);
    if (euMatch) {
        const num = parseFloat(`${euMatch[1]}.${euMatch[3]}`);
        const suf = euMatch[2];
        if (suf === "r" || suf === "R") return num;
        if (suf === "k" || suf === "K") return num * 1e3;
        if (suf === "m") return num * 1e-3;
        if (suf === "M") return num * 1e6;
        if (suf === "g" || suf === "G") return num * 1e9;
    }

    const match = s.match(/^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Zµμ]*)$/);
    if (!match) return NaN;

    const num = parseFloat(match[1]);
    const suf = match[2];
    if (!suf || suf === "r" || suf === "R") return num;
    if (suf === "k" || suf === "K") return num * 1e3;
    if (suf === "M" || suf.toLowerCase() === "meg") return num * 1e6;
    if (suf === "g" || suf === "G") return num * 1e9;
    if (suf === "m") return num * 1e-3;
    if (suf === "u" || suf === "µ" || suf === "μ") return num * 1e-6;
    if (suf === "n") return num * 1e-9;
    if (suf === "p") return num * 1e-12;
    return NaN;
}

export function formatResistance(ohms: number): string {
    if (!isFinite(ohms)) return "—";
    if (ohms >= 1e6) return `${parseFloat((ohms / 1e6).toPrecision(4))} MΩ`;
    if (ohms >= 1e3) return `${parseFloat((ohms / 1e3).toPrecision(4))} kΩ`;
    return `${parseFloat(ohms.toPrecision(4))} Ω`;
}

export function getSeriesBase(series: string): number[] {
    const key = series.toUpperCase().replace(/\+/g, "_");
    if (key === "E24_E48") {
        return Array.from(new Set([...SERIES_DATA.E24, ...SERIES_DATA.E48])).sort((a, b) => a - b);
    }
    if (key === "E24_E96") {
        return Array.from(new Set([...SERIES_DATA.E24, ...SERIES_DATA.E96])).sort((a, b) => a - b);
    }
    if (key in SERIES_DATA) {
        return [...SERIES_DATA[key as keyof typeof SERIES_DATA]];
    }
    throw new Error(`Unknown resistor series: ${series}`);
}

export function getCandidateResistors(
    series: string = "E24_E96",
    rMin: number = 1000,
    rMax: number = 100000,
    customValues?: number[]
): number[] {
    if (customValues && customValues.length > 0) {
        return Array.from(new Set(customValues.filter((v) => isFinite(v) && v > 0).map((v) => Number(v.toPrecision(6))))).sort(
            (a, b) => a - b
        );
    }
    if (rMin <= 0 || rMax < rMin) {
        throw new Error("Resistance bounds must satisfy 0 < rMin <= rMax.");
    }

    const base = getSeriesBase(series);
    const values: number[] = [];
    const minDec = Math.max(-4, Math.floor(Math.log10(rMin)) - 2);
    const maxDec = Math.min(7, Math.ceil(Math.log10(rMax)));
    for (let exp = minDec; exp <= maxDec; exp++) {
        const mult = Math.pow(10, exp);
        for (const b of base) {
            const r = Number((b * mult).toPrecision(6));
            if (r >= rMin * (1 - 1e-9) && r <= rMax * (1 + 1e-9)) {
                values.push(r);
            }
        }
    }
    return Array.from(new Set(values)).sort((a, b) => a - b);
}

function lowerBound(arr: number[], target: number): number {
    let lo = 0;
    let hi = arr.length;
    while (lo < hi) {
        const mid = (lo + hi) >>> 1;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

function buildResult(
    mode: TopologyMode,
    r1: number,
    r2: number,
    r3: number | null,
    rTopEq: number,
    rBotEq: number,
    vref: number,
    voutTarget: number
): DividerResult {
    const vout = vref * (1 + rTopEq / rBotEq);
    const errV = vout - voutTarget;
    const absErr = Math.abs(errV);
    const errPct = (errV / voutTarget) * 100;
    const rTotal = rTopEq + rBotEq;
    const currentUa = (vout / rTotal) * 1e6;
    const powerMw = ((vout * vout) / rTotal) * 1e3;
    return { mode, r1, r2, r3, rTopEq, rBotEq, rTotal, vout, errV, absErr, errPct, currentUa, powerMw };
}

export function solveTB(values: number[], voutTarget: number, vref: number, maxErr: number): DividerResult[] {
    const ratio = voutTarget / vref - 1;
    const n = values.length;
    const results: DividerResult[] = [];
    const seen = new Set<string>();

    for (let i = 0; i < n; i++) {
        const rB = values[i];
        const rTIdeal = rB * ratio;
        const idx = lowerBound(values, rTIdeal);
        for (const ci of [idx, idx - 1]) {
            if (ci >= 0 && ci < n) {
                const rT = values[ci];
                const key = `${rT}|${rB}`;
                if (seen.has(key)) continue;
                seen.add(key);
                const row = buildResult("TB", rT, rB, null, rT, rB, vref, voutTarget);
                if (row.absErr <= maxErr + 1e-12) results.push(row);
            }
        }
    }
    return results;
}

export function solveT1T2B(values: number[], voutTarget: number, vref: number, maxErr: number): DividerResult[] {
    const ratio = voutTarget / vref - 1;
    const n = values.length;
    const results: DividerResult[] = [];
    const seen = new Set<string>();

    for (let b = 0; b < n; b++) {
        const rB = values[b];
        const targetSum = rB * ratio;
        let right = n - 1;
        for (let left = 0; left < n; left++) {
            const r1 = values[left];
            while (right > left && r1 + values[right] > targetSum) right--;
            for (const idx2 of [right, right + 1]) {
                if (idx2 >= left && idx2 < n) {
                    const r2 = values[idx2];
                    const key = `${r1}|${r2}|${rB}`;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    const row = buildResult("T1T2B", r1, r2, rB, r1 + r2, rB, vref, voutTarget);
                    if (row.absErr <= maxErr + 1e-12) results.push(row);
                }
            }
            if (r1 > targetSum && right === left) break;
        }
    }
    return results;
}

export function solveTB1B2(values: number[], voutTarget: number, vref: number, maxErr: number): DividerResult[] {
    const ratio = voutTarget / vref - 1;
    const n = values.length;
    const rDesc = values.slice().reverse();
    const gAsc = rDesc.map((r) => 1 / r);
    const results: DividerResult[] = [];
    const seen = new Set<string>();

    for (let t = 0; t < n; t++) {
        const rT = values[t];
        const gTarget = ratio / rT;
        let right = n - 1;
        for (let left = 0; left < n; left++) {
            const g1 = gAsc[left];
            while (right > left && g1 + gAsc[right] > gTarget) right--;
            for (const idx2 of [right, right + 1]) {
                if (idx2 >= left && idx2 < n) {
                    const rA = rDesc[left];
                    const rB = rDesc[idx2];
                    const rB1 = rA <= rB ? rA : rB;
                    const rB2 = rA <= rB ? rB : rA;
                    const key = `${rT}|${rB1}|${rB2}`;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    const rBotEq = (rB1 * rB2) / (rB1 + rB2);
                    const row = buildResult("TB1B2", rT, rB1, rB2, rT, rBotEq, vref, voutTarget);
                    if (row.absErr <= maxErr + 1e-12) results.push(row);
                }
            }
            if (g1 > gTarget && right === left) break;
        }
    }
    return results;
}

export function normalizeMode(mode: string = "TB"): TopologyMode {
    const key = mode.toUpperCase().replace(/[\s+|()]/g, "");
    if (key === "TB" || key === "T1T2B" || key === "TB1B2") return key;
    throw new Error(`Unknown mode: ${mode}. Choose TB, T1T2B, or TB1B2.`);
}

export function optimizeDivider(opts: OptimizeOptions): DividerResult[] {
    const { vout, vref, series = "E24_E96", rMin = 1000, rMax = 100000, maxErr = 0.1, customValues } = opts;
    if (!isFinite(vout) || !isFinite(vref) || vout <= 0 || vref <= 0) {
        throw new Error("vout and vref must be positive numbers.");
    }
    if (vout <= vref) {
        throw new Error("vout must be strictly greater than vref.");
    }
    if (!isFinite(maxErr) || maxErr < 0) {
        throw new Error("maxErr must be >= 0.");
    }

    const mode = normalizeMode(opts.mode || "TB");
    const candidates = getCandidateResistors(series, rMin, rMax, customValues);
    if (candidates.length === 0) return [];

    const results =
        mode === "TB"
            ? solveTB(candidates, vout, vref, maxErr)
            : mode === "T1T2B"
            ? solveT1T2B(candidates, vout, vref, maxErr)
            : solveTB1B2(candidates, vout, vref, maxErr);

    results.sort((a, b) => (a.absErr !== b.absErr ? a.absErr - b.absErr : a.rTotal - b.rTotal));
    return results;
}

export function buildCSV(
    results: DividerResult[],
    vout: number,
    vref: number,
    mode: TopologyMode,
    sep: string = ";",
    decimal: string = "."
): string {
    const fmt = (v: number, d: number): string => {
        const s = v.toFixed(d);
        return decimal !== "." ? s.replace(".", decimal) : s;
    };
    const numStr = (v: number): string => (decimal !== "." ? String(v).replace(".", decimal) : String(v));

    const lines: string[] = [
        `Required output voltage${sep}${sep}${numStr(vout)}${sep}V`,
        `Reference voltage${sep}${sep}${numStr(vref)}${sep}V`,
        `Topology${sep}${sep}${TOPOLOGY_LABELS[mode]}${sep}`,
        "",
    ];

    if (mode === "TB") {
        lines.push(["R_TOP [Ohm]", "R_BOT [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"].join(sep));
        for (const r of results) {
            lines.push([numStr(r.r1), numStr(r.r2), fmt(r.vout, 4), fmt(r.errV, 4), fmt(r.errPct, 4), fmt(r.currentUa, 2), fmt(r.powerMw, 3)].join(sep));
        }
    } else if (mode === "T1T2B") {
        lines.push(["R_TOP1 [Ohm]", "R_TOP2 [Ohm]", "R_BOT [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"].join(sep));
        for (const r of results) {
            lines.push([numStr(r.r1), numStr(r.r2), numStr(r.r3 ?? 0), fmt(r.vout, 4), fmt(r.errV, 4), fmt(r.errPct, 4), fmt(r.currentUa, 2), fmt(r.powerMw, 3)].join(sep));
        }
    } else {
        lines.push(["R_TOP [Ohm]", "R_BOT1 [Ohm]", "R_BOT2 [Ohm]", "V_OUT [V]", "ERR [V]", "ERR [%]", "I [uA]", "P [mW]"].join(sep));
        for (const r of results) {
            lines.push([numStr(r.r1), numStr(r.r2), numStr(r.r3 ?? 0), fmt(r.vout, 4), fmt(r.errV, 4), fmt(r.errPct, 4), fmt(r.currentUa, 2), fmt(r.powerMw, 3)].join(sep));
        }
    }

    return lines.join("\n") + "\n";
}

// --- CLI Entry Point (Node.js) ---
declare const require: any;
declare const module: any;
declare const process: any;

function runCli(): void {
    const fs = require("fs");
    const argv: string[] = process.argv.slice(2);

    const getArg = (flag: string, fallback: string): string => {
        const idx = argv.indexOf(flag);
        return idx >= 0 && idx + 1 < argv.length ? argv[idx + 1] : fallback;
    };
    const hasFlag = (flag: string): boolean => argv.includes(flag);

    if (hasFlag("-h") || hasFlag("--help")) {
        console.log(
            [
                "Usage: node voltdiv.js [options]",
                "",
                "Options:",
                "  --vout VAL       Required output voltage in V (default: 1.1)",
                "  --vref VAL       Reference voltage in V (default: 0.6)",
                "  --mode MODE      TB | T1T2B | TB1B2 (default: TB)",
                "  --series SER     E24 | E48 | E96 | E24_E48 | E24_E96 | E192 (default: E24_E96)",
                "  --custom LIST    Comma/space separated resistor list (e.g. '1k,2.2k,10k')",
                "  --rmin VAL       Minimum resistance (default: 1k)",
                "  --rmax VAL       Maximum resistance (default: 100k)",
                "  --max-err VAL    Max output error in V (default: 0.1)",
                "  --top N          Rows to print (0 = all, default: 20)",
                "  --csv [FILE]     Export CSV (default: voltdiv_YYYY-MM-DD_HHMMSS.csv)",
                "  --sep CHAR       CSV column separator (default: ';')",
                "  --decimal CHAR   CSV decimal separator (default: '.')",
                "  --json           Output JSON",
            ].join("\n")
        );
        return;
    }

    const vout = parseEngValue(getArg("--vout", "1.1"));
    const vref = parseEngValue(getArg("--vref", "0.6"));
    const mode = normalizeMode(getArg("--mode", "TB"));
    const series = getArg("--series", "E24_E96");
    const rMin = parseEngValue(getArg("--rmin", "1k"));
    const rMax = parseEngValue(getArg("--rmax", "100k"));
    const maxErr = parseEngValue(getArg("--max-err", "0.1"));
    const top = parseInt(getArg("--top", "20"), 10);
    const sep = getArg("--sep", ";");
    const decimal = getArg("--decimal", ".");
    const customStr = getArg("--custom", "");
    const customValues = customStr
        ? customStr
              .split(/[\s,;]+/)
              .filter(Boolean)
              .map(parseEngValue)
        : undefined;

    const results = optimizeDivider({ vout, vref, mode, series, rMin, rMax, maxErr, customValues });

    const csvIdx = argv.indexOf("--csv");
    if (csvIdx >= 0) {
        const nextArg = argv[csvIdx + 1];
        const pad = (n: number): string => String(n).padStart(2, "0");
        const now = new Date();
        const ts = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const csvPath = nextArg && !nextArg.startsWith("--") ? nextArg : `voltdiv_${ts}.csv`;
        fs.writeFileSync(csvPath, buildCSV(results, vout, vref, mode, sep, decimal), "utf8");
        if (!hasFlag("--json")) {
            console.log(`Saved ${results.length} results to ${csvPath}`);
        }
    }

    const shown = top > 0 ? results.slice(0, top) : results;
    if (hasFlag("--json")) {
        console.log(
            JSON.stringify(
                {
                    vout,
                    vref,
                    mode,
                    topology: TOPOLOGY_LABELS[mode],
                    total_matches: results.length,
                    results: shown,
                },
                null,
                2
            )
        );
        return;
    }

    console.log(`V_OUT = ${vout} V | V_REF = ${vref} V | Topology = ${TOPOLOGY_LABELS[mode]} | Matches = ${results.length}`);
    if (results.length === 0) {
        console.log("No matching resistor combinations found within the specified constraints.");
        return;
    }

    const headers =
        mode === "TB"
            ? ["#", "R_T", "R_B", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"]
            : mode === "T1T2B"
            ? ["#", "R_T1", "R_T2", "R_B", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"]
            : ["#", "R_T", "R_B1", "R_B2", "V_OUT [V]", "Err [mV]", "Err [%]", "I [uA]", "P [mW]"];

    const rows = shown.map((r, i) => {
        const errMv = r.errV * 1000;
        const errMvStr = Math.abs(errMv) < 0.005 ? "0" : (errMv > 0 ? "+" : "") + errMv.toFixed(2);
        const errPctStr = Math.abs(r.errPct) < 0.0005 ? "0%" : (r.errPct > 0 ? "+" : "") + r.errPct.toFixed(3) + "%";
        const rCols =
            mode === "TB"
                ? [formatResistance(r.r1), formatResistance(r.r2)]
                : [formatResistance(r.r1), formatResistance(r.r2), formatResistance(r.r3 ?? 0)];
        return [String(i + 1), ...rCols, r.vout.toFixed(4), errMvStr, errPctStr, r.currentUa.toFixed(2), r.powerMw.toFixed(3)];
    });

    const widths = headers.map((h, i) => Math.max(h.length, ...rows.map((row) => row[i].length)));
    console.log("");
    console.log(headers.map((h, i) => h.padStart(widths[i])).join("  "));
    console.log(widths.map((w) => "-".repeat(w)).join("  "));
    for (const row of rows) {
        console.log(row.map((c, i) => c.padStart(widths[i])).join("  "));
    }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    try {
        runCli();
    } catch (err: any) {
        console.error(`Error: ${err.message || err}`);
        process.exit(1);
    }
}

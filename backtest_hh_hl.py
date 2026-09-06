#!/usr/bin/env python3
"""
HH-HL Breakout Strategy Backtester
Replicates the Pine Script logic from HH-HL-strategy.pine on CSV OHLC data.

Usage: python3 backtest_hh_hl.py NSE_DLY_SBIN_1W.csv \
[--length 5] [--sl-buffer 1.0] [--output trades.csv] [--report report.txt]
"""

import csv
import argparse
from pathlib import Path


# ─── Pivot Detection ─────────────────────────────────────────────────────────

def detect_pivots(highs, lows, length):
    """
    Replicate ta.pivothigh(length, length) / ta.pivotlow(length, length).
    A pivot high at index P is confirmed at bar P+length.
    Returns: (pivot_high_by_bar, pivot_low_by_bar) — lists of float|None.
    """
    n = len(highs)
    ph = [None] * n
    pl = [None] * n

    for p in range(length, n - length):
        window = range(p - length, p + length + 1)

        # Pivot high: high[p] must be strictly greater than all others in window
        if all(highs[p] > highs[j] for j in window if j != p):
            ph[p + length] = highs[p]

        # Pivot low: low[p] must be strictly less than all others in window
        if all(lows[p] < lows[j] for j in window if j != p):
            pl[p + length] = lows[p]

    return ph, pl


# ─── Strategy ────────────────────────────────────────────────────────────────

def run_backtest(rows, length=21, sl_buffer=1.0):
    """
    Run the HH-HL breakout strategy on OHLC rows.
    Each row: {'time': str, 'open': float, 'high': float, 'low': float, 'close': float}
    Returns: (trades_list, swings_list)
    """
    dates = [r['time'] for r in rows]
    opens = [r['open'] for r in rows]
    highs = [r['high'] for r in rows]
    lows = [r['low'] for r in rows]
    closes = [r['close'] for r in rows]
    n = len(rows)

    pivot_highs, pivot_lows = detect_pivots(highs, lows, length)

    # Swing tracking
    prev_sh = None          # previous swing high
    prev_sl = None          # previous swing low
    last_hh = None          # most recent Higher High
    last_hl = None          # most recent Higher Low

    # State machine (mirrors Pine Script exactly)
    state = 0               # 0=idle, 1=watching, 2=entry_pending, 3=in_trade
    breakout_close = None
    trade_hl = None
    target_price = None
    stop_price = None
    breakout_bar = None

    trades = []
    swings = []
    cur = None              # current open trade dict

    for i in range(n):
        ph, pl = pivot_highs[i], pivot_lows[i]
        o, h, l, c, dt = opens[i], highs[i], lows[i], closes[i], dates[i]

        # ── Swing classification ──────────────────────────────────────────
        new_hh = False
        if ph is not None:
            if prev_sh is not None and ph > prev_sh:
                new_hh = True
                last_hh = ph
                swings.append((i, dt, 'HH', ph))
            else:
                swings.append((i, dt, 'LH' if prev_sh else 'SH', ph))
            prev_sh = ph

        if pl is not None:
            if prev_sl is not None and pl > prev_sl:
                last_hl = pl
                swings.append((i, dt, 'HL', pl))
            else:
                swings.append((i, dt, 'LL' if prev_sl else 'SL', pl))
            prev_sl = pl

        # ── State transitions (same order as Pine Script) ─────────────────

        # New HH → activate setup
        if new_hh and last_hl is not None and state < 2:
            state = 1
            trade_hl = last_hl

        # State 1: wait for close above HH
        if state == 1 and last_hh is not None:
            if c > last_hh:
                breakout_close = c
                breakout_bar = i
                state = 2
            elif c < trade_hl:
                state = 0

        # State 2: entry pending — must be a subsequent bar
        elif state == 2 and breakout_bar is not None and i > breakout_bar and cur is None:
            if h > breakout_close:
                entry_price = max(o, breakout_close)  # gap-up → fill at open
                target_price = breakout_close + (breakout_close - trade_hl)
                stop_price = trade_hl - sl_buffer
                cur = dict(entry_date=dt, entry_bar=i, entry_price=entry_price,
                           target=target_price, stop_loss=stop_price,
                           hh=last_hh, hl=trade_hl, bkout=breakout_close)
                state = 3
            elif c < trade_hl:
                state = 0

        # State 3: manage position — check TP/SL on bars AFTER entry
        elif state == 3 and cur is not None and i > cur['entry_bar']:
            hit_sl = l <= cur['stop_loss']
            hit_tp = h >= cur['target']

            if hit_sl or hit_tp:
                if hit_sl and hit_tp:
                    # Ambiguous bar: closer to open wins
                    reason = 'SL' if abs(o - cur['stop_loss']) <= abs(o - cur['target']) else 'TP'
                elif hit_sl:
                    reason = 'SL'
                else:
                    reason = 'TP'

                exit_price = cur['stop_loss'] if reason == 'SL' else cur['target']
                # Account for gap: if open already past the level
                if reason == 'SL' and o < cur['stop_loss']:
                    exit_price = o
                if reason == 'TP' and o > cur['target']:
                    exit_price = o

                pnl = exit_price - cur['entry_price']
                cur.update(exit_date=dt, exit_bar=i, exit_price=exit_price,
                           reason=reason, pnl=pnl,
                           pnl_pct=pnl / cur['entry_price'] * 100,
                           bars=i - cur['entry_bar'])
                trades.append(cur)
                cur = None
                state = 0

    # Close any open trade at last bar
    if cur is not None:
        pnl = closes[-1] - cur['entry_price']
        cur.update(exit_date=dates[-1], exit_bar=n-1, exit_price=closes[-1],
                   reason='OPEN', pnl=pnl,
                   pnl_pct=pnl / cur['entry_price'] * 100,
                   bars=n - 1 - cur['entry_bar'])
        trades.append(cur)

    return trades, swings


# ─── Reporting ────────────────────────────────────────────────────────────────

def build_report(trades, swings, length, sl_buffer):
    """Build report as a list of lines."""
    lines = []
    w = lines.append
    hh_c = sum(1 for s in swings if s[2] == 'HH')
    hl_c = sum(1 for s in swings if s[2] == 'HL')
    lh_c = sum(1 for s in swings if s[2] == 'LH')
    ll_c = sum(1 for s in swings if s[2] == 'LL')

    w(f"\n{'=' * 105}")
    w(f"  HH-HL BREAKOUT STRATEGY — BACKTEST REPORT   (length={length}, sl_buffer={sl_buffer})")
    w(f"{'=' * 105}")
    w(f"  Swings → HH: {hh_c}  HL: {hl_c}  LH: {lh_c}  LL: {ll_c}  (total: {len(swings)})")

    if not trades:
        w("\n  No trades generated.\n")
        return lines

    sep = '─' * 105
    w(f"\n{sep}")
    w(f"{'#':>3} {'Entry Date':>12} {'Entry':>9} {'Exit Date':>12} {'Exit':>9} "
      f"{'Rsn':>4} {'P&L':>9} {'P&L%':>7} {'Bars':>4} │ "
      f"{'HH':>9} {'HL':>9} {'Target':>9} {'SL':>9}")
    w(sep)

    for idx, t in enumerate(trades, 1):
        w(f"{idx:>3} {t['entry_date']:>12} {t['entry_price']:>9.2f} "
          f"{t['exit_date']:>12} {t['exit_price']:>9.2f} "
          f"{t['reason']:>4} {t['pnl']:>+9.2f} {t['pnl_pct']:>+6.2f}% {t['bars']:>4} │ "
          f"{t['hh']:>9.2f} {t['hl']:>9.2f} {t['target']:>9.2f} {t['stop_loss']:>9.2f}")
    w(sep)

    total = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    tp_ct = sum(1 for t in trades if t['reason'] == 'TP')
    sl_ct = sum(1 for t in trades if t['reason'] == 'SL')
    open_ct = sum(1 for t in trades if t['reason'] == 'OPEN')
    total_pnl = sum(t['pnl'] for t in trades)

    w(f"\n  Total trades : {total}  (TP: {tp_ct}  SL: {sl_ct}  Open: {open_ct})")
    w(f"  Win rate     : {len(wins)/total*100:.1f}%  ({len(wins)}W / {len(losses)}L)")
    w(f"  Total P&L    : {total_pnl:+.2f}")
    w(f"  Avg P&L      : {total_pnl/total:+.2f}  "
      f"(avg win: {sum(t['pnl'] for t in wins)/max(len(wins), 1):+.2f}  "
      f"avg loss: {sum(t['pnl'] for t in losses)/max(len(losses), 1):+.2f})")
    w(f"  Best trade   : {max(t['pnl'] for t in trades):+.2f}")
    w(f"  Worst trade  : {min(t['pnl'] for t in trades):+.2f}")
    w(f"  Avg bars held: {sum(t['bars'] for t in trades)/total:.1f}")

    if wins and losses:
        avg_w = sum(t['pnl'] for t in wins) / len(wins)
        avg_l = abs(sum(t['pnl'] for t in losses) / len(losses))
        rr = avg_w / avg_l if avg_l > 0 else float('inf')
        w(f"  Reward:Risk  : {rr:.2f}")

    w('')
    return lines


def export_trades_csv(trades, swings, path):
    """Write trades and swings to CSV files for validation."""
    # Trades CSV
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['#', 'entry_date', 'entry_price', 'exit_date', 'exit_price',
                         'reason', 'pnl', 'pnl_pct', 'bars_held',
                         'hh_level', 'hl_level', 'target', 'stop_loss', 'breakout_close'])
        for idx, t in enumerate(trades, 1):
            writer.writerow([
                idx, t['entry_date'], f"{t['entry_price']:.4f}",
                t['exit_date'], f"{t['exit_price']:.4f}",
                t['reason'], f"{t['pnl']:.4f}", f"{t['pnl_pct']:.2f}",
                t['bars'], f"{t['hh']:.4f}", f"{t['hl']:.4f}",
                f"{t['target']:.4f}", f"{t['stop_loss']:.4f}", f"{t['bkout']:.4f}"
            ])

    # Swings CSV (same directory, swings_ prefix)
    swing_path = Path(path).parent / f"swings_{Path(path).name}"
    with open(swing_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['bar_index', 'date', 'type', 'price'])
        for s in swings:
            writer.writerow([s[0], s[1], s[2], f"{s[3]:.4f}"])

    return swing_path


# ─── CSV Reader ───────────────────────────────────────────────────────────────

def read_csv(path):
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                'time':  r['time'].strip(),
                'open':  float(r['open']),
                'high':  float(r['high']),
                'low':   float(r['low']),
                'close': float(r['close']),
            })
    return rows


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='HH-HL Breakout Strategy Backtester')
    parser.add_argument('csv_file', help='Path to OHLC CSV file')
    parser.add_argument('--length', type=int, default=21, help='Pivot lookback (default: 21)')
    parser.add_argument('--sl-buffer', type=float, default=1.0, help='SL buffer in points (default: 1.0)')
    parser.add_argument('--output', '-o', help='Export trades to CSV file')
    parser.add_argument('--report', '-r', help='Save text report to file')
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return 1

    print(f"Loading {csv_path.name} ...")
    rows = read_csv(csv_path)
    print(f"  {len(rows)} bars loaded  ({rows[0]['time']} → {rows[-1]['time']})")

    trades, swings = run_backtest(rows, length=args.length, sl_buffer=args.sl_buffer)

    # Build and print report
    report_lines = build_report(trades, swings, args.length, args.sl_buffer)
    report_text = '\n'.join(report_lines)
    print(report_text)

    # Save report to file
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report_text + '\n')
        print(f"  Report saved to {args.report}")

    # Export trades CSV
    if args.output:
        swing_path = export_trades_csv(trades, swings, args.output)
        print(f"  Trades saved to {args.output}")
        print(f"  Swings saved to {swing_path}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

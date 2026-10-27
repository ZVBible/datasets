#!/usr/bin/env python3
"""Evaluate all-pairs gzip NCD over BSB verses against TSK cross-references.

Inputs (RUNDIR): verses.json, clen.u16, pair.u16, sym.u16 (see README) and a
TSK file: either a JSON map {fromVid: [[toVid, votes]]}
or tsk-edges.tsv from build-tsk-edges.mjs.

NCD(x,y) = (C(xy) - min(C(x),C(y))) / max(C(x),C(y)),  C = gzip -9 length.
Variants
  xy    C(xy) with the query verse first (one concatenation order)
  sym   C(xy) := min(C(x\\ny), C(y\\nx))  (both orders; primary)
  csls  sym re-ranked with a hubness correction: 2*ncd - r(x) - r(y), where
        r(v) = mean sym-NCD of v's 10 nearest neighbours (CSLS-style)
  minlen sym, but queries and candidates must have >= MINLEN words

Outputs (RUNDIR/out): evaluation.json, top-50 neighbours per variant (.npz),
high-similarity pair list, example candidates.

Usage: python3 analyze.py RUNDIR TSKFILE [--workers 8] [--minlen 8]
"""
import argparse, json, pathlib, time, gzip
from multiprocessing import Pool
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('tsk')
ap.add_argument('--workers', type=int, default=8)
ap.add_argument('--minlen', type=int, default=8)
ap.add_argument('--keep', type=int, default=50)
args = ap.parse_args()
RUN = pathlib.Path(args.run); OUT = RUN / 'out'; OUT.mkdir(exist_ok=True)
KEEP = args.keep
KS = [1, 5, 10, 20]
BINS = np.linspace(0, 1.3, 651)  # 0.002 wide

V = json.loads((RUN / 'verses.json').read_text())['verses']
N = len(V)
vid = np.array([v['vid'] for v in V], dtype=np.int64)
book = vid // 1_000_000
chap = (vid // 1000) % 1000
words = np.array([len(v['norm'].split()) for v in V])
C = np.fromfile(RUN / 'clen.u16', dtype='<u2').astype(np.float32)
idx_of = {int(x): i for i, x in enumerate(vid)}

# ---- TSK -> undirected neighbour sets (index space) ----
edges = []
p = pathlib.Path(args.tsk)
if p.suffix == '.json':
    for f, lst in json.loads(p.read_text()).items():
        for t, v in lst:
            edges.append((int(f), int(t), int(v)))
else:
    for line in p.read_text().splitlines():
        f, t, v = map(int, line.split('\t')); edges.append((f, t, v))
dropped = sum(1 for f, t, _ in edges if f not in idx_of or t not in idx_of)
self_loops = sum(1 for f, t, _ in edges if f == t)
U = [dict() for _ in range(N)]  # neighbour -> max votes (either direction)
for f, t, v in edges:
    if f in idx_of and t in idx_of and f != t:
        a, b = idx_of[f], idx_of[t]
        U[a][b] = max(U[a].get(b, 0), v); U[b][a] = max(U[b].get(a, 0), v)
tsk_pairs = sum(len(u) for u in U) // 2

def group(b):
    g = ['OT' if b <= 39 else 'NT']
    if b <= 5: g.append('Law (Gen-Deut)')
    elif b <= 17: g.append('History (Josh-Esth)')
    elif b in (19, 20): g.append('Psalms+Proverbs')
    elif b <= 22: g.append('Job/Eccl/Song')
    elif b <= 39: g.append('Prophets (Isa-Mal)')
    elif b <= 43: g.append('Gospels')
    elif b == 44: g.append('Acts')
    elif b <= 65: g.append('Epistles (Rom-Jude)')
    else: g.append('Revelation')
    return g

def ncd_row(Mrow, i):
    ci = C[i]
    lo = np.minimum(ci, C); hi = np.maximum(ci, C)
    d = (Mrow.astype(np.float32) - lo) / hi
    d[i] = np.inf
    return d

def topk(d, k):
    part = np.argpartition(d, k)[:k]
    order = np.lexsort((part, d[part]))
    return part[order]

def init():
    global PM, SM
    PM = np.memmap(RUN / 'pair.u16', dtype='<u2', mode='r', shape=(N, N))
    SM = np.memmap(RUN / 'sym.u16', dtype='<u2', mode='r', shape=(N, N))

def pass1(rows):
    res = {'rows': rows, 'top': {}, 'topd': {}, 'ranks': {}, 'hist': {}, 'r10': [], 'tskhist': np.zeros(len(BINS) - 1, np.int64)}
    for var in ('xy', 'sym'):
        res['top'][var] = np.zeros((len(rows), KEEP), np.int32)
        res['topd'][var] = np.zeros((len(rows), KEEP), np.float32)
        res['ranks'][var] = []
        res['hist'][var] = np.zeros(len(BINS) - 1, np.int64)
    for r, i in enumerate(rows):
        for var, MM in (('xy', PM), ('sym', SM)):
            d = ncd_row(np.asarray(MM[i]), i)
            t = topk(d, KEEP)
            res['top'][var][r] = t; res['topd'][var][r] = d[t]
            if var == 'sym':
                res['hist'][var] += np.histogram(d[i + 1:], BINS)[0]  # unordered pairs once
                res['r10'].append(float(d[t[:10]].mean()))
                nb = np.fromiter((j for j in U[i] if j > i), np.int64)
                if nb.size: res['tskhist'] += np.histogram(d[nb], BINS)[0]
            else:
                res['hist'][var] += np.histogram(d[np.isfinite(d)], BINS)[0]
            if U[i]:
                nb = np.fromiter(U[i].keys(), np.int64)
                s = np.sort(d)
                rk = np.searchsorted(s, d[nb], side='left') + 1  # 1 + #strictly closer
                res['ranks'][var].append((i, nb.astype(np.int32), rk.astype(np.int32), d[nb]))
    return res

def pass2(rows):
    """CSLS + min-length variants, and high-similarity pair collection (sym)."""
    res = {'rows': rows, 'top': {}, 'ranks': {}, 'pairs': []}
    for var in ('csls', 'minlen'):
        res['top'][var] = np.zeros((len(rows), KEEP), np.int32); res['ranks'][var] = []
    for r, i in enumerate(rows):
        d = ncd_row(np.asarray(SM[i]), i)
        hi = np.nonzero(d[i + 1:] <= PAIR_CUT)[0] + i + 1
        for j in hi: res['pairs'].append((i, int(j), float(d[j])))
        # CSLS
        a = 2 * d - R10[i] - R10
        a[i] = np.inf
        t = topk(a, KEEP); res['top']['csls'][r] = t
        if U[i]:
            nb = np.fromiter(U[i].keys(), np.int64)
            rk = np.searchsorted(np.sort(a), a[nb], side='left') + 1
            res['ranks']['csls'].append((i, nb.astype(np.int32), rk.astype(np.int32), a[nb]))
        # min-length filter
        if words[i] >= args.minlen:
            m = d.copy(); m[SHORT] = np.inf
            t = topk(m, KEEP); res['top']['minlen'][r] = t
            nbl = [j for j in U[i] if not SHORT[j]]
            if nbl:
                nb = np.array(nbl, np.int64)
                rk = np.searchsorted(np.sort(m), m[nb], side='left') + 1
                res['ranks']['minlen'].append((i, nb.astype(np.int32), rk.astype(np.int32), m[nb]))
        else:
            res['top']['minlen'][r] = -1
    return res

def chunks(n, size=64):
    return [list(range(a, min(n, a + size))) for a in range(0, n, size)]

def collect(results, var):
    top = np.zeros((N, KEEP), np.int32); ranks = []
    for res in results:
        top[res['rows']] = res['top'][var]; ranks += res['ranks'].get(var, [])
    return top, ranks

def evaluate(top, ranks, qmask=None, cand_ok=None):
    """recall/precision/hit@K and rank stats over query verses with TSK refs."""
    ranks_by_i = {i: (nb, rk) for i, nb, rk, _ in ranks}
    out = {}
    qs = [i for i in ranks_by_i if (qmask is None or qmask[i])]
    allr = np.concatenate([ranks_by_i[i][1] for i in qs]) if qs else np.array([])
    out['queries'] = len(qs); out['tsk_refs'] = int(allr.size)
    if not qs: return out
    for K in KS:
        rec = []; prec = []; hit = []
        for i in qs:
            nb, rk = ranks_by_i[i]
            h = int((rk <= K).sum())
            rec.append(h / len(nb)); prec.append(h / K); hit.append(h > 0)
        out[f'recall@{K}'] = round(float(np.mean(rec)), 4)
        out[f'precision@{K}'] = round(float(np.mean(prec)), 4)
        out[f'hit@{K}'] = round(float(np.mean(hit)), 4)
        out[f'micro_recall@{K}'] = round(float((allr <= K).mean()), 4)
    out['rank_mean'] = round(float(allr.mean()), 1)
    out['rank_median'] = float(np.median(allr))
    out['rank_p25'] = float(np.percentile(allr, 25)); out['rank_p75'] = float(np.percentile(allr, 75))
    return out

def hq(hist, qs):
    c = np.cumsum(hist) / hist.sum()
    return {str(q): round(float(BINS[1:][np.searchsorted(c, q)]), 3) for q in qs}

if __name__ == '__main__':
    t0 = time.time()
    with Pool(args.workers, initializer=init) as pool:
        R1 = pool.map(pass1, chunks(N), chunksize=1)
    print(f'pass1 {time.time() - t0:.0f}s', flush=True)
    R10 = np.zeros(N, np.float32)
    for res in R1: R10[res['rows']] = res['r10']
    hist_sym = sum(r['hist']['sym'] for r in R1); hist_xy = sum(r['hist']['xy'] for r in R1)
    tskhist = sum(r['tskhist'] for r in R1)
    cum = np.cumsum(hist_sym)
    # collect every unordered pair at or below the 1-in-10,000 all-pairs quantile
    PAIR_CUT = float(BINS[1:][np.searchsorted(cum / cum[-1], 1e-4)])
    SHORT = words < args.minlen
    with Pool(args.workers, initializer=init) as pool:
        R2 = pool.map(pass2, chunks(N), chunksize=1)
    print(f'pass2 {time.time() - t0:.0f}s', flush=True)

    tops = {}; rks = {}
    for var in ('xy', 'sym'):
        tops[var], rks[var] = collect(R1, var)
        tops[var + '_d'] = np.zeros((N, KEEP), np.float32)
        for res in R1: tops[var + '_d'][res['rows']] = res['topd'][var]
    for var in ('csls', 'minlen'):
        tops[var], rks[var] = collect(R2, var)
    np.savez_compressed(OUT / 'topk.npz', vid=vid, **tops, r10=R10)

    ev = {'N': N, 'tsk_edges_input': len(edges), 'tsk_edges_dropped_missing_verse': dropped,
          'tsk_self_loops': self_loops, 'tsk_undirected_pairs': tsk_pairs,
          'all_unordered_pairs': int(N * (N - 1) // 2), 'minlen_words': args.minlen,
          'random_baseline_precision@K': round(float(np.mean([len(u) / (N - 1) for u in U if u])), 5)}
    ev['variants'] = {v: evaluate(tops[v], rks[v]) for v in ('xy', 'sym', 'csls')}
    ev['variants']['minlen'] = evaluate(tops['minlen'], rks['minlen'])
    # same query set as minlen, for a fair comparison
    ev['variants']['sym_on_minlen_queries'] = evaluate(tops['sym'], rks['sym'], qmask=~SHORT)
    # breakdowns (sym)
    groups = sorted({g for b in range(1, 67) for g in group(b)})
    ev['by_group_sym'] = {g: evaluate(tops['sym'], rks['sym'], qmask=np.array([g in group(int(b)) for b in book])) for g in groups}
    # length bins
    qb = np.percentile(words, [25, 50, 75])
    bins = [(0, qb[0]), (qb[0], qb[1]), (qb[1], qb[2]), (qb[2], 1e9)]
    ev['by_length_sym'] = {}
    for lo, hi in bins:
        m = (words > lo) & (words <= hi) if lo else words <= hi
        e = evaluate(tops['sym'], rks['sym'], qmask=m)
        e['top1_ncd_mean'] = round(float(tops['sym_d'][m, 0].mean()), 4)
        ev['by_length_sym'][f'{int(lo)}<words<={int(hi) if hi < 1e9 else "max"}'] = e
    # votes strata (sym): recall of strong vs weak TSK refs
    allv = []; allrk = []
    for i, nb, rk, _ in rks['sym']:
        allv += [U[i][j] for j in nb]; allrk.append(rk)
    allv = np.array(allv); allrk = np.concatenate(allrk)
    ev['by_votes_sym'] = {}
    for lo, hi in [(1, 4), (5, 19), (20, 99), (100, 10**6)]:
        m = (allv >= lo) & (allv <= hi)
        ev['by_votes_sym'][f'{lo}-{hi}'] = {'refs': int(m.sum()), **{f'within_top{K}': round(float((allrk[m] <= K).mean()), 4) for K in KS}, 'rank_median': float(np.median(allrk[m]))}
    # distributions
    qs = [1e-6, 1e-5, 1e-4, 1e-3, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95]
    ev['ncd_quantiles_all_pairs_sym'] = hq(hist_sym, qs)
    ev['ncd_quantiles_tsk_pairs_sym'] = hq(tskhist, qs)
    ev['ncd_quantiles_all_pairs_xy'] = hq(hist_xy, qs)
    np.savez_compressed(OUT / 'hist.npz', bins=BINS, all_sym=hist_sym, tsk_sym=tskhist, all_xy=hist_xy)
    # high-similarity pairs
    pairs = [p for r in R2 for p in r['pairs']]
    pairs.sort(key=lambda p: p[2])
    def adj(i, j): return book[i] == book[j] and chap[i] == chap[j] and abs(int(vid[i]) - int(vid[j])) <= 2
    ev['pair_cut_1e-4'] = PAIR_CUT
    table = []
    for q in [1e-6, 1e-5, 3e-5, 1e-4]:
        thr = float(BINS[1:][np.searchsorted(cum / cum[-1], q)])
        sel = [p for p in pairs if p[2] <= thr]
        intsk = sum(1 for i, j, _ in sel if j in U[i])
        nontsk = [(i, j) for i, j, _ in sel if j not in U[i]]
        table.append({'quantile': q, 'ncd_threshold': thr, 'pairs': len(sel), 'in_tsk': intsk,
                      'in_tsk_frac': round(intsk / max(1, len(sel)), 4), 'not_in_tsk': len(nontsk),
                      'not_in_tsk_adjacent(<=2 verses)': sum(1 for i, j in nontsk if adj(i, j)),
                      'not_in_tsk_same_chapter': sum(1 for i, j in nontsk if book[i] == book[j] and chap[i] == chap[j]),
                      'not_in_tsk_both_short(<minlen words)': sum(1 for i, j in nontsk if SHORT[i] and SHORT[j]),
                      'not_in_tsk_distant_and_long': sum(1 for i, j in nontsk if not adj(i, j) and not SHORT[i] and not SHORT[j])})
    ev['threshold_table'] = table
    # hubs: in-degree in sym top-10
    indeg = np.bincount(tops['sym'][:, :10].ravel(), minlength=N)
    hub = np.argsort(-indeg)[:25]
    ev['hubs_sym_top10_indegree'] = [{'ref': V[h]['ref'], 'indegree': int(indeg[h]), 'words': int(words[h]), 'text': V[h]['text']} for h in hub]
    ev['runtime_analysis_s'] = round(time.time() - t0)
    (OUT / 'evaluation.json').write_text(json.dumps(ev, indent=1))
    with gzip.open(OUT / 'high-sim-pairs.tsv.gz', 'wt') as f:
        f.write('ref_a\tref_b\tncd_sym\tin_tsk_votes\tadjacent\twords_a\twords_b\n')
        for i, j, d in pairs:
            f.write(f"{V[i]['ref']}\t{V[j]['ref']}\t{d:.4f}\t{U[i].get(j, 0)}\t{int(adj(i, j))}\t{words[i]}\t{words[j]}\n")
    print(json.dumps({k: ev[k] for k in ('variants', 'threshold_table')}, indent=1))
    print(f'total {time.time() - t0:.0f}s')

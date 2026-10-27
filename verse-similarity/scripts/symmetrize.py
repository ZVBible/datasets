#!/usr/bin/env python3
"""Build sym.u16 = min(C(x_i\\n x_j), C(x_j\\n x_i)) from pair.u16 (tiled transpose).

Usage: python3 symmetrize.py RUNDIR
"""
import sys, pathlib, time
import numpy as np

run = pathlib.Path(sys.argv[1])
N = int(np.fromfile(run / 'clen.u16', dtype='<u2').size)
M = np.memmap(run / 'pair.u16', dtype='<u2', mode='r', shape=(N, N))
S = np.memmap(run / 'sym.u16', dtype='<u2', mode='w+', shape=(N, N))
T = 2048
t0 = time.time()
for a in range(0, N, T):
    for b in range(a, N, T):
        A = np.asarray(M[a:a + T, b:b + T])
        B = np.asarray(M[b:b + T, a:a + T]).T
        m = np.minimum(A, B)
        S[a:a + T, b:b + T] = m
        S[b:b + T, a:a + T] = m.T
    print(f'tile row {a // T + 1}/{(N + T - 1) // T}  {time.time() - t0:.0f}s', flush=True)
S.flush()
print('sym.u16 done')

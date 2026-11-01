# S7 Scalper (M1) - tuning log

One row per run you want to remember. Change ONE thing at a time, rerun, and note what happened.
Judge a change on the walk-forward (out-of-sample) result and on the cost x2 run, never on in-sample numbers alone.
A scalper that is not profitable at --cost-mult 2 will not survive real fills.

| date | what I changed (param: old -> new) | command | trades | exp R | PF | cost x2 exp R | walk-forward OOS exp R | verdict / next step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | baseline (defaults in params.py) |  |  |  |  |  |  |  |

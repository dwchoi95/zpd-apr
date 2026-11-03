# Original-release history gate: implementation amendment (before fitting)

This continues the September 15 history gate, not a change to v5. A configured
source path in src/cli.py led to the existing read-only CodeNet release under
/Users/cdw/VSCode/aria/data/Project_CodeNet. New outputs remain inside zpd-apr.
Do not modify that source tree. Release-snapshot completeness is distinct from
complete lifetime behavior or observed assistance.

## Fixed population and provenance

Use exactly the 23 problem IDs in the previously inventoried legacy archive as
a fixed development problem roster, but rebuild from ALL original metadata users
and available source languages for those problems. This is a development study
on previously exposed problems, not a new independent confirmatory benchmark.
The roster is not selected using prediction results. No eventual-AC, minimum-user-
problem-count, normalized-deduplication, first-AC truncation, or history-length
filter is applied. Current is Python and non-AC with at least one strictly prior
same-user/problem submission. All earlier languages are preserved; immediate
next metadata rows are never skipped on language change or missing next code.

Order-ambiguous prefixes/next boundaries and unavailable observed source are
reported separately. No observed next submission is censored, not a failure.
The endpoint is conditional on an observed next submission, not abandonment or
learning. Primary data retain 102,560 prefixes in the supplied snapshot: 71,191
train, 15,608 validation, 15,761 test. SHA256 user assignment uses the original
gate's salt and fixed .70/.85 thresholds; no reshuffling. The builder's
python_non_ac_currents counter covers candidate-containing groups, not all
original Python non-AC rows. Source metadata audit is the full-population reference.
Observed next verdict missingness was checked and is zero in this snapshot.

## Encoding and five arms

Current code has separate signed float64 hashed token unigram/bigram and character
3–5-gram blocks, EACH of dimension 2**18, each individually L2-normalized, with
equal block weights and no final joint normalization. Tokenizer retains partial
tokens on errors; full character features remain. ERRORTOKEN/parser failure is
recorded. No vocabulary/IDF is learned from validation or test.

Common C nuisance: current nominal verdict, tokenization-failure flag, log1p of
code characters, number of prior submissions, and elapsed seconds since the first
observed attempt. Therefore C is current+nuisance, not literally code alone.
H adds the mean of all individually encoded prior programs and prior verdict
frequencies/transitions/last verdict. Sparse unique-code pooling is algebraically
the same mean, retains repeated submissions and avoids dense intermediary rows.
S adds log1p of repeated-current-verdict count, adjacent verdict changes, trailing
exact-code repeat count, mean/max/last token edit fraction and time gap. Token edit
fraction is 1-SequenceMatcher(autojunk=False).ratio. Nominal H features exclude
current; S boundary comparisons include current. No psychological state is labeled.

Donors exactly match problem, RAW current verdict, prior count, and total lexical
token count using the engine tokenizer. They are a different training user,
strictly earlier in timestamp, and selected by minimum fixed donor hash. Future
label values are never used. Donor availability is conditional on the observed-next
cohort, not independent of observation/censoring. Do not claim otherwise.

Arms C_F/H_F/S_F train and evaluate on the common full eligible cohort. H_M/U_M
both train, validate and test on the SAME donor-available subsets. Comparing H_F
trained on more rows against U_M as the provenance contrast is forbidden.
The original two gate contrasts remain H_F vs C_F and H_M vs U_M. S is secondary.
Report all-split code overlap separately from within-test cross-user code collisions
with distinct prior code/verdict sequences. Do not equate those denominators.

## Optimization, power and result discipline

Pin numpy 2.5.2, scipy 1.18.1, scikit-learn 1.9.0 and the recorded Python environment.
SGDClassifier log_loss/L2/optimal, explicit manual shuffled epochs, seeds
2027/2028/2029, alpha 1e-5/1e-4/1e-3, 20 epochs. Per-user row weights are inverse
training frequency scaled to mean one. Select alpha by MEAN of the three seed
validation user-equal NLLs; tie goes to larger alpha. Test prediction averages
three seed probabilities. All alpha/seed results are retained. No test early stopping.

Before main fitting, five user-hash train-only crossfit folds (salt
zpd-history-power-20260915) use FIXED alpha=1e-4, seed=2027 and 20 epochs; no
fold validation hyperparameter tuning. Rebuild donors using only fold-training
users and raw-verdict matching. Estimate variance of per-user OOF paired NLL
differences separately for C/H and U/H. Prospective MDE is
(z_.975 + z_.8)*sqrt(variance/fixed_test_user_count). This is an approximate
planning calculation, not retrospective observed power or a significance gate.
Record missing/unevaluable folds and never impute them. It does not automatically
authorize main fitting. The original paired inference/Holm gate remains unchanged.

Runner provenance flags require actual input/source hashes, completed power evidence,
and a frozen amendment. Boolean constructor flags alone are not a certificate.
Power execution reads TRAIN labels only; main selection reads train/validation;
test opening requires saved model/selection hashes and a persistent exclusive lock.
Current work implements and launches the train-only planning phase first; main
test fitting/opening must not be silently chained without checking those artifacts.

# Synthetic witness: AC-first labels do not guarantee AC-first fitted top-one

2026-09-25. A scalar mathematical counterexample only. No empirical labels,
optimizer, fit, source execution, protocol change or algorithm selection.
It motivates a diagnostic question, not a claim that this caused joint4131's
errors. These scalar features are not claimed to be a realized AST-feature bank.

Take nine candidates with scalar features `0,1,...,7,9` and score `theta*x`.
Only feature9 is AC. The eight nonAC candidates have zero regression and net gain
decreasing with their feature, e.g. `(7-x)/8`; feature7 can be the zero-gain no-op.
Thus the frozen AC/non-regression/net-gain lexicographic preference ranks the AC
above every nonAC, then prefers smaller feature values among the nonACs.

There are eight AC/nonAC pairs with preferred feature-difference sum44, and
28 lower-tier nonAC pairs with preferred difference sum-84. For the mean
pairwise logistic loss, plus any strictly positive quadratic ridge term,

`L(theta) = mean_pairs log(1 + exp(-theta*d_pair)) + lambda*theta^2/2`,

the derivative at zero is `-(44-84)/(2*36) = 5/9 > 0`. Strict convexity and
coercivity imply a unique finite minimizer with `theta < 0`. It selects the
feature0 nonAC even though **every positive theta selects the AC**. Mirroring
the comparisons with equal weights does not change that conclusion.

For comparison only, the single-AC bank softmax loss has zero-point derivative
`mean(0,1,...,7,9)-9 = -44/9 < 0`. With positive quadratic ridge it has a unique
positive minimizer and selects the AC in this example. This is not an empirical
fit or a recommendation to replace the real loss without the pending audit.

The example separates an all-pairs surrogate's optimum from a bank top-one
decision even when AC labels are ordered correctly and a successful linear
score exists. It proves neither global realizability in the real dataset nor
that lower-tier terms dominate its fitted objective. The forthcoming full
own-training audit must report their actual mass, loss and critical mistakes;
the example alone does not authorize reweighting, a new loss or any gate change.

The exact integer sums and `fractions.Fraction` derivatives were checked locally:
9 candidates; pair counts8/28; preferred-difference sums44/-84; gradients5/9 and
-44/9. No coefficients were optimized. Keep this development note out of paper
claims unless its relevance is established by actual controlled evidence.

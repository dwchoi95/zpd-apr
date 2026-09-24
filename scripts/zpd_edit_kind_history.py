"""Pure source-only prototype: partition exact signed AST overlap, not keys.

No I/O, source execution, outcome access, fitting, history selection or released
encoder replacement. Caller supplies the unchanged frozen directed.Delta type.
The integer overlaps retain the original global denominator. Fraction views
prove conservation; summing rounded binary64 kind values need not reproduce the
pooled binary64 bit pattern. No causal/semantic credit is assigned to a kind.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from scripts import zpd_repair_directed_history as directed

VERSION = 'exact_ast_edit_kind_overlap_prototype_v1'
DIRECTED_SOURCE_SHA256 = '39b616f4101c062b55bc3ed58fe7ba0d73196d271bda99ddfa6b856ed53b5c18'
KINDS = ('operator', 'literal', 'identifier', 'other')
_OPERATOR_BASES = (ast.operator, ast.unaryop, ast.boolop, ast.cmpop)


def key_kind(key) -> str:
    """Classify a frozen key without changing the key used for intersection.

Name/arg is a syntactic group, not complete name binding or dataflow analysis.
The caller's frozen signature remains responsible for constructing its typed
path/scalar representation; this function performs no normalization/alignment.
"""
    if (type(key) is not tuple or len(key) != 3 or type(key[0]) is not tuple
            or type(key[1]) is not str or type(key[2]) is not tuple):
        raise ValueError('frozen (path, node-class, scalar-fields) key required')
    try:
        hash(key)
    except TypeError as error:
        raise ValueError('immutable exact key required') from error
    node = getattr(ast, key[1], None)
    if not isinstance(node, type) or not issubclass(node, ast.AST):
        raise ValueError('AST node-class name required')
    if issubclass(node, _OPERATOR_BASES):
        return 'operator'
    if node is ast.Constant:
        return 'literal'
    if node in (ast.Name, ast.arg):
        return 'identifier'
    return 'other'


def _validate(delta):
    if not isinstance(delta, directed.Delta):
        raise TypeError('explicit frozen directed.Delta required')
    if type(delta.available) is not bool or type(delta.mass) is not int or delta.mass < 0:
        raise ValueError('exact Boolean availability and nonnegative integer mass required')
    for counts in (delta.additions, delta.removals):
        if not isinstance(counts, Mapping):
            raise ValueError('signed key-count mappings required')
        for key, count in counts.items():
            key_kind(key)
            if type(count) is not int or count <= 0:
                raise ValueError('strictly positive integer key counts required')
    if set(delta.additions) & set(delta.removals):
        raise ValueError('common keys must already be cancelled between signs')
    if delta.mass != sum(delta.additions.values()) + sum(delta.removals.values()):
        raise ValueError('original mass must equal all signed key counts')
    if not delta.available and delta.mass:
        raise ValueError('unavailable frozen delta must have empty signed counts')


@dataclass(frozen=True)
class KindMatch:
    available: bool
    denominator: int
    same_overlap: tuple[int, int, int, int]
    reverse_overlap: tuple[int, int, int, int]

    def _exact(self, counts):
        return tuple(Fraction(2 * value, self.denominator) if self.denominator else Fraction(0)
                     for value in counts)

    @property
    def exact_same(self) -> tuple[Fraction, ...]:
        return self._exact(self.same_overlap)

    @property
    def exact_reverse(self) -> tuple[Fraction, ...]:
        return self._exact(self.reverse_overlap)

    @property
    def same(self) -> tuple[float, ...]:
        return tuple(float(value) for value in self.exact_same)

    @property
    def reverse(self) -> tuple[float, ...]:
        return tuple(float(value) for value in self.exact_reverse)


def match_kinds(candidate: directed.Delta, history: directed.Delta) -> KindMatch:
    """2×4 signed overlap using full mass, retaining available no-op deltas.

Within each sign intersection the ORIGINAL key is looked up unchanged. The
kind is used only after an exact match, never as a substitute equality key.
Unavailability is distinct from available zero overlap and is not imputed.
"""
    _validate(candidate)
    _validate(history)
    zero = (0, 0, 0, 0)
    if not candidate.available or not history.available:
        return KindMatch(False, 0, zero, zero)
    denominator = candidate.mass + history.mass
    same = [0] * len(KINDS)
    reverse = [0] * len(KINDS)

    def accumulate(left, right, result):
        for key, count in left.items():
            overlap = min(count, right.get(key, 0))
            if overlap:
                result[KINDS.index(key_kind(key))] += overlap

    accumulate(candidate.additions, history.additions, same)
    accumulate(candidate.removals, history.removals, same)
    accumulate(candidate.additions, history.removals, reverse)
    accumulate(candidate.removals, history.additions, reverse)
    return KindMatch(True, denominator, tuple(same), tuple(reverse))


def configuration():
    return dict(version=VERSION, kinds=list(KINDS), directions=['same', 'reverse'],
        directed_source_sha256=DIRECTED_SOURCE_SHA256,
        denominator='original_full_candidate_mass_plus_history_mass',
        intersection='unchanged_exact_typed_AST_keys_before_kind_partition',
        equality='exact_integer_counts_and_Fraction_conservation',
        float_values='individually_rounded_Fraction_no_bitwise_sum_claim',
        unavailable='explicit_available_false_never_imputed',
        empirical_readiness_established=False, fitting_performed=False,
        encoder_replacement_authorized=False)

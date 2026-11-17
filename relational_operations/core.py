"""Exact finite probability-table operations, independent of JIM or hardware.

Fractions and algebra only: no sampling, quantum dynamics, learner, optimizer,
parameter search or service access. Constructed tables are specifications.
"""
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations


def require(value, message):
    if not value:
        raise ValueError(message)


def parity_sign(category):
    return -1 if category.bit_count() % 2 else 1


@dataclass(frozen=True)
class JointTable:
    bits: tuple
    probabilities: tuple

    def __post_init__(self):
        require(1 <= len(self.bits) <= 12 and len(set(self.bits)) == len(self.bits), "1..12 distinct bit labels required")
        require(len(self.probabilities) == 1 << len(self.bits), "Complete binary table required")
        require(all(isinstance(p, Fraction) and p >= 0 for p in self.probabilities), "Nonnegative exact probabilities required")
        require(sum(self.probabilities) == 1, "Probabilities must sum to one")

    @classmethod
    def from_counts(cls, bits, counts):
        require(all(type(c) is int and c >= 0 for c in counts) and sum(counts) > 0, "Nonnegative recorded counts required")
        return cls(tuple(bits), tuple(Fraction(c, sum(counts)) for c in counts))

    def marginal(self, bits):
        bits = tuple(bits)
        require(len(set(bits)) == len(bits) and set(bits) <= set(self.bits), "Unique known marginal labels required")
        positions = [len(self.bits)-1-self.bits.index(b) for b in bits]
        result = [Fraction(0)] * (1 << len(bits))
        for category, probability in enumerate(self.probabilities):
            key = 0
            for position in positions:
                key = (key << 1) | ((category >> position) & 1)
            result[key] += probability
        return tuple(result)

    def full_parity_moment(self):
        return sum(parity_sign(i)*p for i,p in enumerate(self.probabilities))

    def even_probability(self):
        return (1+self.full_parity_moment())/2

    def movement_interval(self):
        even = [p for i,p in enumerate(self.probabilities) if parity_sign(i) == 1]
        odd = [p for i,p in enumerate(self.probabilities) if parity_sign(i) == -1]
        return -min(even), min(odd)

    def move_relationship(self, epsilon):
        epsilon = Fraction(epsilon)
        low, high = self.movement_interval()
        require(low <= epsilon <= high, "Requested relationship exceeds this table's valid interval")
        return JointTable(self.bits, tuple(p+parity_sign(i)*epsilon for i,p in enumerate(self.probabilities)))

    def proper_marginals(self):
        return {bits:self.marginal(bits) for size in range(1,len(self.bits))
                for bits in combinations(self.bits,size)}

    def conditional_lookup(self, given, query):
        """Exact query of a table, not causal intervention or model training."""
        query = tuple(query)
        require(set(given) <= set(self.bits) and set(query) <= set(self.bits), "Known labels required")
        require(len(set(query)) == len(query) and not(set(query)&set(given)), "Distinct query labels outside conditions required")
        require(all(type(v) is int and v in (0,1) for v in given.values()), "Conditions must be binary answers")
        total = Fraction(0)
        out = [Fraction(0)]*(1 << len(query))
        for category, probability in enumerate(self.probabilities):
            values = {bit:(category>>(len(self.bits)-1-j))&1 for j,bit in enumerate(self.bits)}
            if any(values[bit] != value for bit,value in given.items()):
                continue
            key = 0
            for bit in query:
                key = (key<<1)|values[bit]
            out[key] += probability
            total += probability
        return {"conditionProbability":total, "answerProbabilities":None if total==0 else tuple(p/total for p in out)}


def exact(value):
    value=Fraction(value)
    return {"numerator":value.numerator,"denominator":value.denominator,"decimal":float(value)}


def describe(table):
    low,high=table.movement_interval()
    return {"bits":list(table.bits),"probabilities":[exact(p) for p in table.probabilities],
            "movementInterval":[exact(low),exact(high)],
            "evenParityProbability":exact(table.even_probability()),
            "fullParityMoment":exact(table.full_parity_moment()),
            "properMarginals":[{"bits":list(bits),"probabilities":[exact(p) for p in values]}
                               for bits,values in table.proper_marginals().items()]}

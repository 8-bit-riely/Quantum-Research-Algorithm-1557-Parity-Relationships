"""Run ALGO-1557 on a simulated parity circuit or supplied joint counts."""

import argparse
from fractions import Fraction
import json
from pathlib import Path

from relational_operations import JointTable
from relational_operations.extensions import (
    covariance_of_means,
    coverage,
    feature_masks,
    recover_exact_moments,
    table_from_moments,
)


BITS = (2, 1, 0)  # A, B, C, most to least significant in each outcome
WORDS = tuple(f"{index:03b}" for index in range(8))


def ideal_circuit_counts():
    """Return 800 balanced counts representing the exact ideal circuit law."""
    amplitudes = [1] + [0] * 7
    for wire in (2, 1):
        mask = 1 << wire
        for index in range(8):
            if index & mask == 0:
                zero, one = amplitudes[index], amplitudes[index | mask]
                # The common Hadamard factor cancels in the final normalization.
                amplitudes[index] = zero + one
                amplitudes[index | mask] = zero - one
    for control in (2, 1):
        for index in range(8):
            if index & (1 << control) and index & 1 == 0:
                amplitudes[index], amplitudes[index | 1] = amplitudes[index | 1], amplitudes[index]
    norm = sum(amplitude**2 for amplitude in amplitudes)
    return [int(800 * Fraction(amplitude**2, norm)) for amplitude in amplitudes]


def read_counts(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not set(data) <= set(WORDS):
        raise ValueError("Use a JSON object keyed by three-bit strings in A, B, C order")
    counts = [data.get(word, 0) for word in WORDS]
    if any(type(count) is not int or count < 0 for count in counts) or sum(counts) < 2:
        raise ValueError("Supply nonnegative integer counts and at least two observations")
    return counts


def run_hybrid(counts):
    observed = JointTable.from_counts(BITS, counts)
    masks = feature_masks(len(BITS), order=2)
    means, covariance = covariance_of_means(observed, masks, sum(counts))
    recovered = recover_exact_moments(masks, means, covariance, sum(counts))
    table = table_from_moments(BITS, recovered)
    if table != observed:
        raise RuntimeError("Recovered and supplied tables differ")

    given = {2: 1, 1: 0}
    lookup = table.conditional_lookup(given, [0])
    probabilities = lookup["answerProbabilities"]
    if probabilities is None:
        decision = "request evidence (condition absent from supplied observations)"
    elif probabilities[0] == probabilities[1]:
        decision = "abstain (equal empirical probabilities)"
    else:
        decision = f"predict C={int(probabilities[1] > probabilities[0])} (empirical majority)"
    return {
        "count": sum(counts),
        "condition": "A=1, B=0",
        "observations_under_condition": int(sum(counts) * lookup["conditionProbability"]),
        "P(C=1 | A=1, B=0)": None if probabilities is None else str(probabilities[1]),
        "lower_order_masks_missing_without_covariance": coverage(len(BITS), masks)["hiddenMasks"],
        "recovered_parity_moment_ABC": str(recovered[7]),
        "joint_table_recovered_exactly": True,
        "example_host_decision": decision,
    }


def compare_ideal_baseline(counts, result):
    observed = JointTable.from_counts(BITS, counts)
    uniform = JointTable.from_counts(BITS, [1] * 8)
    opposite = uniform.move_relationship(-Fraction(1, 8))
    if observed.proper_marginals() != uniform.proper_marginals() or observed.proper_marginals() != opposite.proper_marginals():
        raise RuntimeError("The ideal controls differ in lower-order statistics")
    if result["P(C=1 | A=1, B=0)"] != "1":
        raise RuntimeError("The ideal circuit produced an unexpected conditional")
    result["same_one_and_two_bit_statistics"] = True
    result["compatible_conditional_values_from_pairs_alone"] = ["0", "1/2", "1"]
    result["pairs_only_host_decision"] = "request joint evidence (conditional is not identified)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, help="JSON joint counts in A, B, C bit order")
    args = parser.parse_args()
    try:
        counts = read_counts(args.counts) if args.counts else ideal_circuit_counts()
    except (OSError, ValueError) as error:
        parser.error(str(error))
    result = run_hybrid(counts)
    if args.counts is None:
        compare_ideal_baseline(counts, result)
    print(json.dumps({"source": "user_supplied_joint_counts" if args.counts else "ideal_simulated_circuit", **result}, indent=2))


if __name__ == "__main__":
    main()

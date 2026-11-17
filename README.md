# ALGO-1557 · Parity Relationships

**Original mathematics, algorithm, and research by Riely Dionne.**

I developed ALGO-1557 to recover higher-order relationships from retained measurements, test what data summaries preserve, and certify changes that keep individual and pairwise distributions fixed.

## What it can do today

ALGO-1557 works with joint probability tables for binary variables. The variables can come from quantum measurements, classical observations, or a model. The source of the data matters and should travel with every result.

| Operation | What it gives you |
| --- | --- |
| **Recover relationships from retained statistics** | Reconstruct higher-order parity moments when the necessary statistics from the same observations are available. For four bits, single and pair means give 10 of the 15 nonconstant moments. The retained cross-covariances can supply the other five. With all 15, reconstruct the full 16-cell table. |
| **Check what the data can determine** | When only individual and pair distributions are available, certify which outcomes can carry mass and which joint tables fit those constraints. Keep unresolved alternatives visible. |
| **Change a relationship while preserving lower-order statistics** | Design valid alternative joint tables with the same individual and pair distributions. Use them to test whether a decision depends on a relationship your baseline summary discarded. |
| **Answer conditional queries** | Calculate a conditional distribution from a supplied joint table. Keep the result tied to that table and flag conditioning events the evidence cannot support. |

## A small example

Suppose `000`, `011`, `101`, and `110` each have probability ¼, with all other outcomes at zero. Every bit is balanced. Every pair looks independent. But once `A=1` and `B=0`, the table implies `C=1` with probability 1. A model that only sees single and pair distributions cannot distinguish this table from three independent balanced bits, where the same conditional is ½.

That difference can matter to a decision. If an action depends on `C` given `A` and `B`, retain the joint evidence or the relevant parity statistic. If you have only the single and pair summaries, flag the missing relationship or request a measurement that could resolve it. This example uses a constructed distribution.

## Using it in a hybrid system

1. **Collect joint evidence.** Use a classical source, simulator, or quantum processor to obtain outcomes with the relevant bits measured together. Keep the sample count, bit order, and provenance. Preserve joint counts or the required means and covariances computed from the same observations.
2. **Check and reconstruct on the CPU.** Use ALGO-1557 to verify the data contract and recover the relationships the evidence supports. Pass forward the reconstructed table or conditional, its provenance, and any unresolved constraints.
3. **Give the decision system a choice.** Compare candidate actions with the recovered relationship available. When compatible tables support different choices, the host can request more evidence, defer the decision, or choose an action that holds across the remaining possibilities.
4. **Measure whether it helps.** On withheld tasks, compare the same decision system with and without the higher-order information. Match the observations and budget. Record decisions, task outcomes, and whether uncertainty was handled correctly. Include collection and processing costs before making a performance claim.

In **Algorith-Red-01**, this is an integration design. **ALGO-1287** is the quantum intelligence core and **ALGO-1636** contributes its own learned features. ALGO-1557 can supply verified relationships to that decision path. The next validation is to show when those relationships change an actual decision and improve its outcome under a matched comparison.

## Verified so far

- The archived decoder recovered all **793 nonconstant moments through order four** on **32 retained records**, using 78 feature means and 715 selected covariance entries. All **64 four-bit reconstructions** matched their source histograms exactly.
- The geometry analysis checked **1,024 coordinate maxima** across those 64 projections using exact rational certificates.
- The standalone package passed **13 tests on Fedora**. These results verify the reported calculations on retained data. They leave physical control, new-task improvement, and any quantum advantage as separate questions.

## Source availability

The November 3, 2026 source archive has been withdrawn from the current branch while its license notice is reviewed. This README documents the research and its current capabilities. It grants no new software license.

import math
import unittest

import pandas as pd

from business_cycle_backtester.signals import classify_business_cycle, classify_macro_regime
from business_cycle_backtester.stats import state_conditioned_stats, transition_matrix


class BacktesterCoreTests(unittest.TestCase):
    def test_business_cycle_phase_map(self):
        self.assertEqual(classify_business_cycle(0.1, 0.1), "Expansion")
        self.assertEqual(classify_business_cycle(0.1, -0.1), "Slowdown")
        self.assertEqual(classify_business_cycle(-0.1, -0.1), "Contraction")
        self.assertEqual(classify_business_cycle(-0.1, 0.1), "Recovery")

    def test_macro_regime_map(self):
        self.assertEqual(classify_macro_regime(1, -1), "Goldilocks")
        self.assertEqual(classify_macro_regime(1, 1), "Reflation")
        self.assertEqual(classify_macro_regime(-1, 1), "Inflation")
        self.assertEqual(classify_macro_regime(-1, -1), "Deflation")

    def test_state_conditioned_stats_and_transitions(self):
        df = pd.DataFrame(
            {
                "phase": ["Expansion", "Expansion", "Slowdown", "Slowdown"],
                "asset": [0.01, 0.02, -0.01, 0.00],
            }
        )
        stats = state_conditioned_stats(df, ["phase"], ["asset"], min_obs=2)
        expansion = stats[stats["state"].eq("Expansion")].iloc[0]
        self.assertEqual(expansion["observations"], 2)
        self.assertFalse(math.isnan(expansion["sharpe"]))

        tm = transition_matrix(df["phase"], normalize=False)
        self.assertEqual(tm.loc["Expansion", "Expansion"], 1)
        self.assertEqual(tm.loc["Expansion", "Slowdown"], 1)


if __name__ == "__main__":
    unittest.main()

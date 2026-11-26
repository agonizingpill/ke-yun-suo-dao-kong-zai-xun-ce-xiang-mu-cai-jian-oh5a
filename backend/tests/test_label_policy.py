import unittest
from types import SimpleNamespace

from lab.constants import PanelState
from lab.label_policy import (
    TERMINAL_PANEL_STATES,
    apply_label_correction,
    invalidation_reason,
    is_open_candidate,
    panels_using_run,
    snapshot_eligible,
    snapshot_order,
)


def panel(panel_id, state):
    return SimpleNamespace(id=panel_id, state=state, invalidation_reason=None)


class LabelPolicyTest(unittest.TestCase):
    def setUp(self):
        # 候选 1、2 的训练快照用到 run 7；候选 3 未使用；样本 9 仅属于候选 3。
        self.panels = [
            panel(1, PanelState.QUEUED.value),
            panel(2, PanelState.TRIAL.value),
            panel(3, PanelState.ISSUED.value),
            panel(4, PanelState.REJECTED.value),
            panel(5, PanelState.INVALID.value),
            panel(6, PanelState.ARCHIVED.value),
        ]
        self.samples = {
            1: {7, 8},
            2: {7},
            3: {7, 9},
            4: {7},
            5: {7},
            6: {8},
        }

    def test_only_panels_using_run_are_candidates(self):
        self.assertEqual({row.id for row in panels_using_run(self.panels, self.samples, 7)}, {1, 2, 3, 4, 5})
        self.assertEqual({row.id for row in panels_using_run(self.panels, self.samples, 9)}, {3})
        self.assertEqual(panels_using_run(self.panels, self.samples, 999), [])

    def test_open_queued_and_trial_candidates_become_invalid(self):
        affected = apply_label_correction(
            self.panels, self.samples, run_id=7, run_ref="Y7-07-A", actor="duan",
            previous_value=False, current_value=True, reason="复看发现漏标",
        )
        self.assertEqual({row.id for row in affected}, {1, 2})
        for row in affected:
            self.assertEqual(row.state, PanelState.INVALID.value)
            self.assertIn("Y7-07-A", row.invalidation_reason)
            self.assertIn("复看发现漏标", row.invalidation_reason)

    def test_issued_archived_rejected_and_invalid_are_untouched(self):
        apply_label_correction(
            self.panels, self.samples, run_id=7, run_ref="Y7-07-A", actor="duan",
            previous_value=False, current_value=True, reason="复看发现漏标",
        )
        untouched = {row.id: row.state for row in self.panels if row.id in (3, 4, 5, 6)}
        self.assertEqual(untouched, {
            3: PanelState.ISSUED.value,
            4: PanelState.REJECTED.value,
            5: PanelState.INVALID.value,
            6: PanelState.ARCHIVED.value,
        })

    def test_panel_not_using_run_keeps_state(self):
        affected = apply_label_correction(
            self.panels, self.samples, run_id=99, run_ref="X3-01-A", actor="duan",
            previous_value=True, current_value=False, reason="误标",
        )
        self.assertEqual(affected, [])
        self.assertTrue(all(is_open_candidate(row) for row in self.panels[:2]))

    def test_terminal_states_cover_issued_and_archived(self):
        # 已签发面板及其归档旧版在标签更正后照常使用，留档不动。
        self.assertIn(PanelState.ISSUED, TERMINAL_PANEL_STATES)
        self.assertIn(PanelState.ARCHIVED, TERMINAL_PANEL_STATES)

    def test_reason_text_records_both_labels_and_actor(self):
        text = invalidation_reason("Y7-02-P", "duan", True, False, "人工复核更正")
        self.assertIn("Y7-02-P", text)
        self.assertIn("duan", text)
        self.assertIn("需人工复看", text)
        self.assertIn("无需复看", text)
        self.assertIn("人工复核更正", text)

    def test_snapshot_requires_all_measures(self):
        measures = [1, 2, 3]
        complete = {"id": 1, "marks": {1: 1.0, 2: 2.0, 3: 3.0}}
        partial = {"id": 2, "marks": {1: 1.0, 3: 3.0}}
        self.assertTrue(snapshot_eligible(complete, measures))
        self.assertFalse(snapshot_eligible(partial, measures))

    def test_snapshot_order_is_stable_by_day_then_id(self):
        runs = [
            {"id": 4, "day": "2026-11-02"},
            {"id": 2, "day": "2026-11-01"},
            {"id": 1, "day": "2026-11-01"},
            {"id": 9, "day": "2026-11-03"},
        ]
        self.assertEqual([row["id"] for row in snapshot_order(runs)], [1, 2, 4, 9])


if __name__ == "__main__":
    unittest.main()

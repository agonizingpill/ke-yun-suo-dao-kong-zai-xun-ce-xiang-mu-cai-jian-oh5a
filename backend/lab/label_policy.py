"""人工复看标签更正与候选失效的纯规则。

不依赖 ORM 或 Web 框架，方便在没有完整运行环境时用标准库单元测试；
panel_service / run_service 只负责取数、加锁和落库。
"""
from .constants import PanelState

# 源标签更正后仍照常使用的面板：已签发及其归档的前一版。
FROZEN_PANEL_STATES = frozenset({PanelState.ISSUED, PanelState.ARCHIVED})
# 终态候选不会再被标签更正翻案。
TERMINAL_PANEL_STATES = frozenset(
    FROZEN_PANEL_STATES | {PanelState.INVALID, PanelState.REJECTED},
)


def panels_using_run(panels, sample_run_ids, run_id):
    """候选中训练样本快照引用了指定班次记录的面板。"""
    return [panel for panel in panels
            if run_id in sample_run_ids.get(panel.id, frozenset())]


def is_open_candidate(panel):
    """未签发、未归档且未处于失效/退回终态的候选，标签更正后必须失效。"""
    return panel.state not in TERMINAL_PANEL_STATES


def invalidation_reason(run_ref, actor, previous_value, current_value, reason):
    return (f"训练依据 {run_ref} 的人工复看标签已由 {actor} 更正"
            f"（{_mark_text(previous_value)}→{_mark_text(current_value)}），"
            f"本候选的冻结样本与现行标签不符，须重新申报。原因：{reason}")


def apply_label_correction(panels, sample_run_ids, run_id, run_ref, actor,
                           previous_value, current_value, reason):
    """返回被失效的面板列表（原地更新 state 与失效原因）。"""
    detail = invalidation_reason(run_ref, actor, previous_value, current_value, reason)
    affected = []
    for panel in panels_using_run(panels, sample_run_ids, run_id):
        if is_open_candidate(panel):
            panel.state = PanelState.INVALID.value
            panel.invalidation_reason = detail
            affected.append(panel)
    return affected


def _mark_text(value):
    return "需人工复看" if value else "无需复看"


def snapshot_eligible(run, measure_ids):
    """只有包含全部项目读数的班次才能进入训练快照（与拟合抽数规则一致）。"""
    return set(measure_ids).issubset(run["marks"])


def snapshot_order(runs):
    """申报快照按日期、再按班次记录主键稳定排序，保证 SHA256 可复算。"""
    return sorted(runs, key=lambda item: (item["day"], item["id"]))

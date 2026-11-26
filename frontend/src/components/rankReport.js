import {esc, pct, shortDay} from '../format.js';

export function rankReport(metrics) {
  return `<dl class="scoreline">
    <div><dt>回看记录</dt><dd>${metrics.samples}</dd></div>
    <div><dt>全自选项 · 平衡准确率</dt><dd>${pct(metrics.full_score)}</dd></div>
    <div><dt>裁减自选项 · 平衡准确率</dt><dd>${pct(metrics.compact_score)}</dd></div>
   </dl>
   <details><summary>按日期留组的三折误差</summary><ul>
   ${metrics.folds.map(row => `<li>${row.held_days.map(shortDay).map(esc).join('、')} → ${pct(row.compact)}</li>`).join('')}
   </ul></details>`;
}

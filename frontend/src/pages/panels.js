import {cardHead, label, note, seriesOptions} from '../components/board.js';
import {compactTable} from '../components/marks.js';
import {rankReport} from '../components/rankReport.js';
import {formData, handle, inlineError} from '../form.js';
import {esc} from '../format.js';
import {client, member} from '../session.js';
import {panelStates, shifts} from '../types.js';

const reviewText = value => value ? '需人工复看' : '无需复看';

function frozenSamples(panel) {
  if (!panel.training_samples?.length) return '';
  return `<details class="frozen"><summary>申报时冻结的训练依据（${panel.training_samples.length} 笔，标签留档不随后续更正变化）</summary>
    <table class="manifest"><thead><tr><th scope="col">回放编号</th><th scope="col">日期</th><th scope="col">班次</th><th scope="col">冻结标签</th></tr></thead>
    <tbody>${panel.training_samples.map(sample => `<tr><th scope="row">${esc(sample.run_ref)}</th>
      <td>${esc(sample.day)}</td><td>${esc(shifts[sample.shift])}</td><td>${esc(reviewText(sample.camera_review))}</td></tr>`).join('')}
    </tbody></table></details>`;
}

function rankings(active, catalog, role) {
  if (!active) return note('候选尚未创建。记录岗可在右侧提交。');
  return `<article class="rank-sheet" data-panel="${active.id}">
    <header><div><p class="code">${esc(active.reference)}</p><h2>${esc(active.title)}</h2></div>${label(panelStates[active.state], active.state)}</header>
    <p>采样截止 ${esc(active.cutoff_day)} · 自选预算 ${active.budget} 项</p>
    <p>${esc(active.explanation || '正在按日期留组计算。')}</p>
    ${active.invalidation_reason ? note(active.invalidation_reason) : ''}
    ${active.metrics ? rankReport(active.metrics) : ''}
    ${frozenSamples(active)}
    ${active.items.length ? `<div class="ledger">${compactTable(active.items,catalog)}</div>` : ''}
    ${active.state === 'invalid' ? note('该候选已失效：请重新申报候选，重训结果出来后早晚班需重新复核。') : ''}
    ${active.state === 'trial' && role === 'supervisor' ? `<form id="issue-form">
      <label class="check"><input type="checkbox" name="confirm" required>仅发布模拟回看影子版</label>
      <button type="submit">签发影子版</button>${inlineError}</form>` : ''}
    ${active.state === 'trial' ? `<a href="#trials?id=${active.id}">核对两班试行回执</a>` : ''}
  </article>`;
}

export async function panelsPage(root, ctx) {
  const [{measures,series}, panels] = await Promise.all([client().catalog(), client().panels()]);
  const id = Number(ctx.query.get('id'));
  const active = panels.find(row => row.id === id) || panels[0];
  const role = member().role;
  root.innerHTML = `${cardHead('影子面板', '锁定项目始终保留。申报时冻结训练样本与标签，只有自选回看项参加递归特征消除。')}
    <div class="ranking-layout">
      <nav class="panel-list" aria-label="候选版本"><button id="refresh" type="button" class="subtle">刷新计算结果</button>
        ${panels.map(row => `<a href="#panel?id=${row.id}" class="${row === active ? 'chosen' : ''}"><strong>${esc(row.reference)}</strong>
          <small>${esc(panelStates[row.state])}${row.invalidation_reason ? ' · 标签更正失效' : ''}</small></a>`).join('')}
      </nav>
      ${rankings(active, measures, role)}
      ${role === 'technician' ? `<aside class="entry"><h2>候选试行单</h2><form id="candidate-form">
        <label>车型<select name="series_id">${seriesOptions(series, series.find(r => r.code === 'Y7')?.id)}</select></label>
        <label>名称<input name="title" placeholder="Y7 双班回看试行" required minlength="4"></label>
        <label>训练截止日<input type="date" name="cutoff_day" value="2026-11-18" required></label>
        <label>自选项保留数<input type="number" name="budget" min="1" max="5" value="2" required></label>
        <button type="submit">提交 RFE 分析</button>${inlineError}</form></aside>` : ''}
    </div>`;
  root.querySelector('#refresh').onclick = () => ctx.refresh();
  handle(root.querySelector('#candidate-form'), async form => {
    const row = await client().propose(formData(form, ['series_id','budget']));
    ctx.flash(`候选 ${row.reference} 已排队，训练样本与标签已冻结。`);
    location.hash = `panel?id=${row.id}`;
  });
  handle(root.querySelector('#issue-form'), async form => {
    const row = await client().issue(active.id, form.elements.confirm.checked);
    ctx.refresh(`已签发 ${row.reference}；签发时的训练依据与分数已留档。`);
  });
}

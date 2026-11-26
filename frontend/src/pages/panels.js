import {cardHead, label, note, seriesOptions} from '../components/board.js';
import {compactTable} from '../components/marks.js';
import {rankReport} from '../components/rankReport.js';
import {formData, handle, inlineError} from '../form.js';
import {esc} from '../format.js';
import {client, member} from '../session.js';
import {panelStates} from '../types.js';

function rankings(active, catalog, role) {
  if (!active) return note('候选尚未创建。记录岗可在右侧提交。');
  return `<article class="rank-sheet" data-panel="${active.id}">
    <header><div><p class="code">${esc(active.reference)}</p><h2>${esc(active.title)}</h2></div>${label(panelStates[active.state], active.state)}</header>
    <p>采样截止 ${esc(active.cutoff_day)} · 自选预算 ${active.budget} 项</p>
    <p>${esc(active.explanation || '正在按日期留组计算。')}</p>
    ${active.metrics ? rankReport(active.metrics) : ''}
    ${active.items.length ? `<div class="ledger">${compactTable(active.items,catalog)}</div>` : ''}
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
  root.innerHTML = `${cardHead('影子面板', '锁定项目始终保留。只有自选回看项参加递归特征消除。')}
    <div class="ranking-layout">
      <nav class="panel-list" aria-label="候选版本"><button id="refresh" type="button" class="subtle">刷新计算结果</button>
        ${panels.map(row => `<a href="#panel?id=${row.id}" class="${row === active ? 'chosen' : ''}"><strong>${esc(row.reference)}</strong>
          <small>${esc(panelStates[row.state])}</small></a>`).join('')}
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
    ctx.flash(`候选 ${row.reference} 已排队。`);
    location.hash = `panel?id=${row.id}`;
  });
  handle(root.querySelector('#issue-form'), async form => {
    const row = await client().issue(active.id, form.elements.confirm.checked);
    ctx.refresh(`已签发 ${row.reference}。`);
  });
}

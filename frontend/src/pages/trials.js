import {cardHead, label, note} from '../components/board.js';
import {formData, handle, inlineError} from '../form.js';
import {esc} from '../format.js';
import {client, member} from '../session.js';
import {panelStates, shifts, trialStates} from '../types.js';

function station(shift, entry, run, canReview, panelInvalid) {
  return `<article class="shift-board ${esc(shift)}">
    <h2>${esc(shifts[shift])}</h2>
    ${entry ? `<p>${label(trialStates[entry.state], entry.state)} <strong>${esc(run?.ref)}</strong> · ${esc(run?.day)}</p>
      <p>${esc(entry.notes)}</p><p class="sub">${esc(entry.filed_by)} 提交
      ${entry.reviewed_by ? ` · ${esc(entry.reviewed_by)} 复核` : ''}</p>
      ${entry.review_note ? note(entry.review_note) : ''}
      ${panelInvalid ? note('候选已因标签更正失效，本回执随候选冻结，不再接受复核。') : ''}
      ${!panelInvalid && canReview && entry.state === 'recorded' ? `<form data-review="${entry.id}">
        <label>复核意见<input name="note" minlength="4" required></label>
        <button type="submit" value="approve">复核通过</button>
        <button type="submit" value="return" class="subtle">退回补交</button>${inlineError}</form>` : ''}` :
      note('尚未提交此班试行回执。')}
  </article>`;
}

export async function trialsPage(root, ctx) {
  const [panels,runs] = await Promise.all([client().panels(),client().runs()]);
  const active = panels.find(row => row.id === Number(ctx.query.get('id'))) || panels.find(row => row.state === 'trial') || panels[0];
  const history = active ? await client().trials(active.id) : [];
  const role = member().role;
  const panelInvalid = active?.state === 'invalid';
  const eligible = active && !panelInvalid ? runs.filter(row => row.series_id === active.series_id && row.day > active.cutoff_day)
    .filter(run => !history.some(trial => trial.shift === run.shift && trial.state !== 'returned')) : [];
  root.innerHTML = `${cardHead('双班试行', '早报和晚报必须各有一张经复核的同车型记录。重训候选须重新完成早晚班复核。')}
    ${active ? `<label class="filter">影子版<select id="select-panel">
      ${panels.map(row => `<option value="${row.id}" ${row.id === active.id ? 'selected' : ''}>${esc(row.reference)} · ${esc(panelStates[row.state])}</option>`).join('')}
      </select></label>` : note('先递交一个候选面板。')}
    ${panelInvalid ? note(`候选 ${active.reference} 已失效：${active.invalidation_reason || '训练依据的人工标签被更正。'} 请在候选页查看原因并重新申报。`) : ''}
    <div class="shift-layout">${Object.keys(shifts).map(shift => {
        const entry = history.find(row => row.shift === shift);
        return station(shift,entry,runs.find(run => run.id === entry?.run_id),role === 'supervisor',panelInvalid);
      }).join('')}</div>
    ${active?.state === 'trial' && role === 'technician' && eligible.length ? `<section class="entry trial-entry"><h2>补交或登记回执</h2>
    <form id="trial-form">
      <label>截止日后班次<select name="run_id">${eligible.map(run => `<option value="${run.id}">${esc(run.ref)} · ${shifts[run.shift]} · ${esc(run.day)}</option>`).join('')}</select></label>
      <label>说明<input name="notes" minlength="6" placeholder="按影子面板同步回看，原台账完整" required></label>
      <button type="submit">递交本班回执</button>${inlineError}</form></section>` : ''}
    ${active ? `<p><a href="#panel?id=${active.id}">返回面板去留表</a></p>` : ''}`;
  const picker = root.querySelector('#select-panel');
  if (picker) picker.onchange = event => { location.hash = `trials?id=${event.target.value}`; };
  handle(root.querySelector('#trial-form'), async form => {
    const row = await client().report({...formData(form, ['run_id']), panel_id:active.id});
    ctx.refresh(`已提交 ${shifts[row.shift]} 回执。`);
  });
  for (const form of root.querySelectorAll('[data-review]')) {
    form.addEventListener('submit', event => { form.dataset.action = event.submitter?.value; });
    handle(form, async fields => {
      const row = await client().review(form.dataset.review,{note:fields.elements.note.value, approve:form.dataset.action === 'approve'});
      ctx.refresh(`${shifts[row.shift]} · ${trialStates[row.state]}`);
    });
  }
}

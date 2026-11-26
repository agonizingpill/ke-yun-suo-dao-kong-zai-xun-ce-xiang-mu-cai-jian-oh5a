import {cardHead, label, note, seriesOptions} from '../components/board.js';
import {measureInputs, selectedMarks} from '../components/marks.js';
import {formData, handle, inlineError} from '../form.js';
import {esc} from '../format.js';
import {client, member} from '../session.js';
import {shifts} from '../types.js';

const reviewText = value => value ? '需人工复看' : '无需复看';

function rows(runs, series) {
  return runs.map(row => `<tr><th scope="row">${esc(row.ref)}</th><td>${esc(row.day)}</td>
    <td>${esc(shifts[row.shift])}</td><td>${esc(series.find(s => s.id === row.series_id)?.code)}</td>
    <td>${row.marks.length}</td>
    <td>${row.camera_review ? label('需人工复看','locked') : label('无需复看','omitted')}
      ${row.revised ? label('已更正','returned') : ''}</td></tr>`).join('');
}

function revisionTrail(runs) {
  const changed = runs.filter(row => row.revised).flatMap(row =>
    row.revisions.map(item => ({...item, ref: row.ref, day: row.day, shift: row.shift})));
  if (!changed.length) return '';
  return `<section class="ledger"><h2>标签更正留痕</h2>
    <table class="manifest"><thead><tr><th scope="col">回放编号</th><th scope="col">日期</th><th scope="col">班次</th>
      <th scope="col">原值</th><th scope="col">现值</th><th scope="col">更正原因</th><th scope="col">操作人</th></tr></thead>
      <tbody>${changed.map(item => `<tr><th scope="row">${esc(item.ref)}</th><td>${esc(item.day)}</td>
        <td>${esc(shifts[item.shift])}</td>
        <td>${esc(reviewText(item.previous_value))}</td><td>${esc(reviewText(item.current_value))}</td>
        <td>${esc(item.reason)}</td><td>${esc(item.revised_by)}</td></tr>`).join('')}</tbody></table></section>`;
}

function correctionForm(runs) {
  if (member().role !== 'technician') {
    return `<aside class="entry">${note('登记与标签更正由空载记录岗负责。查阅人员可核对日期、人工复看标签与更正留痕。')}</aside>`;
  }
  return `<aside class="entry"><h2>更正人工复看标签</h2>
    <p class="sub">更正会立即生效；未签发且使用该记录训练的候选将失效，已签发面板照常使用。</p>
    <form id="mark-form">
      <label>班次记录<select name="run_id" required>
        ${runs.map(row => `<option value="${row.id}">${esc(row.ref)} · ${esc(row.day)} · ${esc(shifts[row.shift])} · 现：${esc(reviewText(row.camera_review))}</option>`).join('')}
      </select></label>
      <label class="check"><input name="camera_review" type="checkbox">更正后标签为需复看</label>
      <label>更正原因<input name="reason" required minlength="4" maxlength="300" placeholder="人工复看发现原标签填错"></label>
      <button type="submit">提交标签更正</button>${inlineError}</form></aside>`;
}

export async function runsPage(root, ctx) {
  const filter = ctx.query.get('shift') || '';
  const [data, runs] = await Promise.all([client().catalog(), client().runs(filter)]);
  root.innerHTML = `${cardHead('班次记录', '空载试行用实际班次记录。拟合按日期隔开训练与留组，申报时冻结样本与标签。')}
    <div class="side-by-side">
      <section class="ledger">
        <label class="filter">切换值班<select id="shift-filter"><option value="">全部值班</option>
          ${Object.entries(shifts).map(([key,name]) => `<option value="${key}" ${key === filter ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
        <table class="manifest"><thead><tr><th scope="col">回放编号</th><th scope="col">日期</th>
          <th scope="col">班次</th><th scope="col">车型</th><th scope="col">项目数</th><th scope="col">人工标签</th></tr></thead>
          <tbody>${rows(runs.slice(0,24), data.series)}</tbody></table>
        ${runs.length ? `<p class="sub">显示 ${Math.min(runs.length,24)} 笔，当前班次共 ${runs.length} 笔。</p>` : note('没有该班次的记录。')}
        ${revisionTrail(runs)}
      </section>
      <div class="entry-stack">
        ${correctionForm(runs)}
        ${member().role === 'technician' ? `<aside class="entry"><h2>新纪录片段</h2><form id="run-form">
        <label>车型<select name="series_id">${seriesOptions(data.series, data.series.find(r => r.code === 'Y7')?.id)}</select></label>
        <label>回放编号<input name="ref" required pattern="[A-Z0-9\x2D]+" placeholder="Y7-WATCH-24"></label>
        <label>日期<input name="day" type="date" value="2026-11-24" required></label>
        <label>班次<select name="shift"><option value="dawn">早班</option><option value="dusk">晚班</option></select></label>
        <label class="check"><input name="camera_review" type="checkbox">人工标签为需复看</label>
        <fieldset><legend>固定登记及可选读数</legend>${measureInputs(data.measures)}</fieldset>
        <button type="submit">记录空载班次</button>${inlineError}</form></aside>` : ''}
      </div>
    </div>`;
  root.querySelector('#shift-filter').onchange = event => { location.hash = `runs${event.target.value ? '?shift=' + event.target.value : ''}`; };
  handle(root.querySelector('#run-form'), async form => {
    const {series_id, ref, day, shift} = formData(form, ['series_id']);
    const row = await client().logRun({series_id, ref, day, shift,
      camera_review:form.elements.camera_review.checked, marks:selectedMarks(form)});
    ctx.refresh(`已登记 ${row.ref} · ${shifts[row.shift]}。`);
  });
  handle(root.querySelector('#mark-form'), async form => {
    const {run_id, reason} = formData(form, ['run_id']);
    const result = await client().correctMark(run_id, {camera_review: form.elements.camera_review.checked, reason});
    const count = result.invalidated_panels.length;
    ctx.refresh(count
      ? `标签已更正；${count} 个未签发候选失效：${result.invalidated_panels.map(panel => panel.reference).join('、')}。`
      : '标签已更正，没有受影响的未签发候选。');
  });
}

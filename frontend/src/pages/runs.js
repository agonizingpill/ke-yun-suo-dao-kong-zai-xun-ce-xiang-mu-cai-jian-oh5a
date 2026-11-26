import {cardHead, label, note, seriesOptions} from '../components/board.js';
import {measureInputs, selectedMarks} from '../components/marks.js';
import {formData, handle, inlineError} from '../form.js';
import {esc} from '../format.js';
import {client, member} from '../session.js';
import {shifts} from '../types.js';

function rows(runs, series) {
  return runs.map(row => `<tr><th scope="row">${esc(row.ref)}</th><td>${esc(row.day)}</td>
    <td>${esc(shifts[row.shift])}</td><td>${esc(series.find(s => s.id === row.series_id)?.code)}</td>
    <td>${row.marks.length}</td><td>${row.camera_review ? label('需人工复看','locked') : label('无需复看','omitted')}</td></tr>`).join('');
}

export async function runsPage(root, ctx) {
  const filter = ctx.query.get('shift') || '';
  const [data, runs] = await Promise.all([client().catalog(), client().runs(filter)]);
  root.innerHTML = `${cardHead('班次记录', '空载试行用实际班次记录。拟合按日期隔开训练与留组。')}
    <div class="side-by-side">
      <section class="ledger">
        <label class="filter">切换值班<select id="shift-filter"><option value="">全部值班</option>
          ${Object.entries(shifts).map(([key,name]) => `<option value="${key}" ${key === filter ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
        <table class="manifest"><thead><tr><th scope="col">回放编号</th><th scope="col">日期</th>
          <th scope="col">班次</th><th scope="col">车型</th><th scope="col">项目数</th><th scope="col">人工标签</th></tr></thead>
          <tbody>${rows(runs.slice(0,24), data.series)}</tbody></table>
        ${runs.length ? `<p class="sub">显示 ${Math.min(runs.length,24)} 笔，当前班次共 ${runs.length} 笔。</p>` : note('没有该班次的记录。')}
      </section>
      ${member().role === 'technician' ? `<aside class="entry"><h2>新纪录片段</h2><form id="run-form">
        <label>车型<select name="series_id">${seriesOptions(data.series, data.series.find(r => r.code === 'Y7')?.id)}</select></label>
        <label>回放编号<input name="ref" required pattern="[A-Z0-9\x2D]+" placeholder="Y7-WATCH-24"></label>
        <label>日期<input name="day" type="date" value="2026-11-24" required></label>
        <label>班次<select name="shift"><option value="dawn">早班</option><option value="dusk">晚班</option></select></label>
        <label class="check"><input name="camera_review" type="checkbox">人工标签为需复看</label>
        <fieldset><legend>固定登记及可选读数</legend>${measureInputs(data.measures)}</fieldset>
        <button type="submit">记录空载班次</button>${inlineError}</form></aside>` : `<aside class="entry">${note('登记由空载记录岗负责。查阅人员可核对日期与人工复看标签。')}</aside>`}
    </div>`;
  root.querySelector('#shift-filter').onchange = event => { location.hash = `runs${event.target.value ? '?shift=' + event.target.value : ''}`; };
  handle(root.querySelector('#run-form'), async form => {
    const {series_id, ref, day, shift} = formData(form, ['series_id']);
    const row = await client().logRun({series_id, ref, day, shift,
      camera_review:form.elements.camera_review.checked, marks:selectedMarks(form)});
    ctx.refresh(`已登记 ${row.ref} · ${shifts[row.shift]}。`);
  });
}

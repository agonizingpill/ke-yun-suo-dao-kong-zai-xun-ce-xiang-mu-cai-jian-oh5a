import {esc} from '../format.js';
import {label} from './board.js';

export function measureInputs(measures) {
  return measures.map(measure => `<label class="measure-form">
    <span>${esc(measure.label)} ${measure.locked ? label('目录锁定','locked') : ''}</span>
    <input name="mark-${measure.id}" type="number" min="0" max="10000" step="any"
       ${measure.locked ? 'value="1" required' : 'value="" placeholder="—"'} aria-label="${esc(measure.label)}">
  </label>`).join('');
}

export function selectedMarks(form) {
  return [...new FormData(form).entries()].filter(([name, value]) => name.startsWith('mark-') && value !== '')
    .map(([name, value]) => ({measure_id:Number(name.slice(5)), value:Number(value)}));
}

export function compactTable(items, catalog) {
  const ranking = new Map(items.map(row => [row.id, row]));
  return `<table class="manifest"><thead><tr><th scope="col">项目</th><th scope="col">面板去留</th><th scope="col">递归排名</th></tr></thead>
   <tbody>${catalog.map(measure => {
      const item = ranking.get(measure.id);
      return `<tr><th scope="row"><small>${esc(measure.code)}</small> ${esc(measure.label)}</th>
        <td>${!item ? '—' : measure.locked ? label('强制保留','locked') : item.selected ? label('保留','kept') : label('暂不并看','omitted')}</td>
        <td>${item?.rank ?? '—'}</td></tr>`;
    }).join('')}</tbody></table>`;
}

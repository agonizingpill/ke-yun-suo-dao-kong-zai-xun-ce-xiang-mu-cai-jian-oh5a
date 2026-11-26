import {cardHead, label, note} from '../components/board.js';
import {esc} from '../format.js';
import {client} from '../session.js';

export async function catalogPage(root) {
  const {measures, series} = await client().catalog();
  root.innerHTML = `${cardHead('巡测项目', '班组用这份目录区分固定登记和镜头回看自选项。')}
    <div class="side-by-side">
      <section class="ledger" aria-label="巡测项目目录">
      <table class="manifest"><thead><tr><th scope="col">编号</th><th scope="col">观察项目</th><th scope="col">记录来源</th><th scope="col">目录规则</th></tr></thead>
       <tbody>${measures.map(row => `<tr><td class="code">${esc(row.code)}</td><th scope="row">${esc(row.label)}<small> · ${esc(row.unit)}</small></th>
         <td>${esc(row.source)}</td><td>${row.locked ? label('锁定','locked') : label('自选','omitted')}</td></tr>`).join('')}</tbody></table></section>
      <aside class="series-rail"><h2>车型板</h2>
      ${series.map(row => `<article class="cabin"><p class="code">${esc(row.code)}</p><h3>${esc(row.label)}</h3>
        ${row.current_panel_id ? `<a href="#panel?id=${row.current_panel_id}">查现行影子版</a>` : note('等待样本')}</article>`).join('')}
      </aside>
    </div>`;
}

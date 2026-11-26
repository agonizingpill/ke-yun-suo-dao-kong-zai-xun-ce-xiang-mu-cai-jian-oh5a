import {esc} from '../format.js';
import {roles} from '../types.js';

export const label = (word, type = '') => `<span class="label ${esc(type)}">${esc(word)}</span>`;
export const note = text => `<div class="strip">${esc(text)}</div>`;
export const cardHead = (name, text) => `<header class="board-head"><h1>${esc(name)}</h1><p>${esc(text)}</p></header>`;

export function seriesOptions(series, selected) {
  return series.map(row => `<option value="${row.id}" ${row.id === selected ? 'selected' : ''}>${esc(row.code)} · ${esc(row.label)}</option>`).join('');
}

const panels = [['catalog','巡测项目'], ['runs','班次记录'], ['panel','影子面板'], ['trials','双班试行']];

export const body = (active, profile) => `<header class="top">
 <a class="identity" href="#catalog">云峡<span>索道</span></a>
 <nav aria-label="巡测工作区">${panels.map(([key, text]) => `<a href="#${key}" ${key === active ? 'aria-current="page"' : ''}>${text}</a>`).join('')}</nav>
 <div class="profile">${esc(roles[profile.role])} · ${esc(profile.display_name)} <button id="exit" class="subtle">退出</button></div>
 </header><main class="content">
 <p class="flag">模拟训练 · 影子面板仅供并行回看</p><section id="messages" aria-live="polite"></section><div id="panel"></div></main>`;

import {body,note} from './components/board.js';
import {esc} from './format.js';
import {member,useSession} from './session.js';
import {loginPage} from './pages/login.js';
import {catalogPage} from './pages/catalog.js';
import {runsPage} from './pages/runs.js';
import {panelsPage} from './pages/panels.js';
import {trialsPage} from './pages/trials.js';

const app = document.querySelector('#app');
const routes = {catalog:catalogPage, runs:runsPage, panel:panelsPage, trials:trialsPage};
let toast = '';

async function render() {
  const [path, query] = location.hash.slice(1).split('?');
  if (!member() || path === 'login') return loginPage(app, render);
  const current = Object.hasOwn(routes,path) ? path : 'catalog';
  app.innerHTML = body(current,member());
  app.querySelector('#exit').onclick = () => {
    useSession(null);
    location.hash = 'login';
  };
  if (toast) { app.querySelector('#messages').innerHTML = note(toast); toast = ''; }
  const page = app.querySelector('#panel');
  try {
    await routes[current](page,{query:new URLSearchParams(query),
      refresh: message => { toast = typeof message === 'string' ? message : ''; render(); },
      flash: message => { toast = message; },
    });
  } catch (error) {
    if (!page.isConnected) return;
    if (error.status === 401 || error.status === 403) {
      useSession(null);
      location.hash = 'login';
      return;
    }
    page.innerHTML = `<div class="strip" role="alert">${esc(error.message)} <button id="retry">再试</button></div>`;
    page.querySelector('#retry').onclick = render;
  }
}

window.addEventListener('hashchange',render);
render();

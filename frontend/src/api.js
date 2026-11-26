import {request} from './http.js';

export const signIn = data => request('/auth/login', {method:'POST', data});

export function withSession(token) {
  const get = path => request(path, {token});
  const post = (path, data) => request(path, {token, data, method:'POST'});
  return {
    catalog: () => get('/catalog'),
    runs: (shift = '') => get(`/runs${shift ? '?shift=' + encodeURIComponent(shift) : ''}`),
    panels: () => get('/panels'),
    trials: panel => get(`/trials${panel ? '?panel_id=' + panel : ''}`),
    logRun: data => post('/runs', data),
    correctMark: (id, data) => request(`/runs/${id}/review-mark`, {token, data, method:'PATCH'}),
    propose: data => post('/panels', data),
    issue: (id, confirmed) => post(`/panels/${id}/issue`, {confirm_shadow:confirmed}),
    report: data => post('/trials', data),
    review: (id, data) => post(`/trials/${id}/review`, data),
  };
}

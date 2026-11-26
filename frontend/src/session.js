import {withSession} from './api.js';

const key = 'ropeway-shadow-crew';
let current = JSON.parse(sessionStorage.getItem(key) || 'null');

export const member = () => current?.profile;
export const client = () => withSession(current?.access_token);

export function useSession(session) {
  current = session;
  if (session) sessionStorage.setItem(key, JSON.stringify(session));
  else sessionStorage.removeItem(key);
}

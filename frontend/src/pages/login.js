import {signIn} from '../api.js';
import {formData, handle, inlineError} from '../form.js';
import {useSession} from '../session.js';

export function loginPage(root, redraw) {
  root.innerHTML = `<main class="entrance">
    <section class="station">
      <div class="track" aria-hidden="true"><span></span><span></span><span></span></div>
      <div><p>云峡索道 · 例检班</p><h1>空载巡测<br>影子面板</h1><p>同一列车，早晚两班。回看项目可以少，锁定目录照常核对。</p></div>
    </section>
    <section class="credentials">
      <h2>值班人员登录</h2><p>使用你的空载记录或复核账号。</p>
      <form id="login-form">
        <label>用户名<input name="username" autocomplete="username" required></label>
        <label>密码<input name="password" type="password" autocomplete="current-password" required></label>
        <button type="submit">打开值班板</button>${inlineError}</form>
      <small>演示班组：duan、ning、qin</small>
    </section>
  </main>`;
  handle(root.querySelector('form'), async form => {
    useSession(await signIn(formData(form)));
    if (location.hash === '#catalog') redraw();
    else location.hash = 'catalog';
  });
}

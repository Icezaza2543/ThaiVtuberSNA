/* One static entry point. Query routes also work on hosts without rewrite rules. */
(async () => {
  'use strict';
  const views = {
    network: { title: 'เครือข่าย | Thai VTuber SNA', css: 'styles.css', scripts: ['temporal-state.js', 'app.js', 'observatory-ui.js'] },
    research: { title: 'ผลวิเคราะห์ | Thai VTuber SNA', css: 'research/research_dashboard.css', scripts: ['research/research_dashboard.js'] },
    report: { title: 'รายงานต้นแบบ | Thai VTuber SNA', css: 'research/research_v2.css', scripts: ['research/research_v2.js'] },
  };
  const requested = new URLSearchParams(location.search).get('view');
  const name = Object.hasOwn(views, requested) ? requested : 'network';
  const view = views[name];
  const status = document.getElementById('site-status');
  document.title = view.title;
  document.body.dataset.view = name;
  document.querySelector(`.site-nav [data-view="${name}"]`).setAttribute('aria-current', 'page');
  try {
    await new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = view.css;
      link.onload = resolve;
      link.onerror = reject;
      document.head.insertBefore(link, document.querySelector('link'));
    });
    document.body.append(document.getElementById(`view-${name}`).content.cloneNode(true));
    document.querySelectorAll('template').forEach(template => template.remove());
    status.remove();
    for (const src of view.scripts) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.body.append(script);
      });
    }
    if (name === 'network') await initApp();
    if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
  } catch (error) {
    status.setAttribute('role', 'alert');
    status.textContent = 'โหลดหน้าไม่สำเร็จ โปรดลองรีเฟรชอีกครั้ง';
    if (!status.isConnected) document.querySelector('.site-nav').after(status);
    console.error('Unable to load site view', error);
  }
})();

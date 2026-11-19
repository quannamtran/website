// Header diagnostics, loaded only with ?debug=header in the address.
// Shows, live, what the browser is doing to the top menu, so a disappearing
// menu can be traced to its cause (an extension, a setting, an old copy...).
(function () {
  var header = document.querySelector('.site-header');
  var log = [];
  var box = document.createElement('pre');
  box.setAttribute('style', 'position:fixed;left:8px;bottom:8px;z-index:2147483647;max-width:min(560px,calc(100vw - 16px));max-height:60vh;overflow:auto;margin:0;padding:10px 12px;background:#fff;color:#000;border:2px solid #d17a22;border-radius:8px;font:12px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap;box-shadow:0 8px 24px rgba(0,0,0,.25)');
  document.documentElement.appendChild(box);

  function describe(el) {
    if (!el) return 'nothing';
    var s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.className && typeof el.className === 'string') s += '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.');
    return s;
  }
  function oddities(el) {
    var cs = getComputedStyle(el), out = [];
    ['transform', 'filter', 'perspective', 'contain', 'willChange', 'backdropFilter', 'zoom', 'overflow'].forEach(function (k) {
      var v = cs[k];
      if (v && v !== 'none' && v !== 'auto' && v !== 'visible' && v !== 'normal' && v !== '1') out.push(k + ': ' + v);
    });
    return out;
  }
  // Anything else that changes the header's attributes or style is recorded.
  new MutationObserver(function (list) {
    list.forEach(function (m) {
      if (m.type === 'attributes' && !/^(class|style|popover)$/.test(m.attributeName) ) return;
      var v = header.getAttribute(m.attributeName) || '';
      if (m.attributeName === 'style' && /^transform: translateY\(-?[\d.]+px\);?$|^$/.test(v)) return; // our own safety net
      if (m.attributeName === 'class' && /^site-header( is-scrolled)?$/.test(v)) return;
      log.push(new Date().toLocaleTimeString() + ' header ' + m.attributeName + ' → "' + v.slice(0, 80) + '"');
    });
  }).observe(header, { attributes: true });
  new MutationObserver(function () {
    ['html', 'body'].forEach(function (t) {
      var el = document.querySelector(t), a = [];
      for (var i = 0; i < el.attributes.length; i++) a.push(el.attributes[i].name);
      var key = t + ' attrs: ' + a.join(' ');
      if (log.indexOf(key) === -1) log.push(key);
    });
  }).observe(document.documentElement, { attributes: true, subtree: false, childList: true });

  function render() {
    var cs = getComputedStyle(header), r = header.getBoundingClientRect();
    var atTop = document.elementFromPoint(window.innerWidth / 2, Math.max(2, r.height / 2));
    var foreign = [].slice.call(document.styleSheets).filter(function (s) { return !s.href || s.href.indexOf(location.origin) !== 0; }).length;
    var extNodes = [].slice.call(document.documentElement.children).concat([].slice.call(document.body.children))
      .filter(function (el) { return !/^(HEAD|BODY|HEADER|MAIN|FOOTER|SECTION|SCRIPT|NOSCRIPT|PRE|A|IFRAME|LINK|STYLE)$/.test(el.tagName) || /grammarly|acrobat|claude|extension/i.test(el.id + ' ' + el.className); })
      .map(describe);
    var scripts = [].slice.call(document.scripts).map(function (s) { return (s.src.match(/main\.js\?v=\w+/) || [])[0]; }).filter(Boolean);
    var css = [].slice.call(document.querySelectorAll('link[rel=stylesheet]')).map(function (l) { return (l.href.match(/style\.css\?v=\w+/) || [])[0]; }).filter(Boolean);
    var lines = [
      'HEADER DIAGNOSTIC  (screenshot this box, scrolled down)',
      'browser: ' + (navigator.userAgent.match(/(Chrome|Edg|Firefox|Version)\/[\d.]+/g) || [navigator.userAgent]).join(' '),
      'files: ' + css.concat(scripts).join('  '),
      'window: ' + window.innerWidth + '×' + window.innerHeight + '  zoom ' + Math.round(window.devicePixelRatio * 100) + '%  scrollY ' + Math.round(window.scrollY) + '  scroller ' + describe(document.scrollingElement),
      'header box: top ' + Math.round(r.top) + '  height ' + Math.round(r.height) + '  width ' + Math.round(r.width),
      'header css: ' + ['position', 'display', 'visibility', 'opacity', 'zIndex', 'transform'].map(function (k) { return k + '=' + cs[k]; }).join(' '),
      'top layer: ' + (header.matches && (function () { try { return header.matches(':popover-open'); } catch (e) { return 'n/a'; } })()),
      'what is at the top of the screen: ' + describe(atTop) + (atTop && header.contains(atTop) ? '  (the menu: OK)' : '  ← COVERS THE MENU'),
      'html: ' + (oddities(document.documentElement).join('; ') || 'normal'),
      'body: ' + (oddities(document.body).join('; ') || 'normal'),
      'extra stylesheets (not from this site): ' + foreign,
      'extra elements on the page: ' + (extNodes.join(', ') || 'none')
    ].concat(log.length ? ['changes seen:'].concat(log.slice(-8)) : []);
    box.textContent = lines.join('\n');
  }
  render();
  window.addEventListener('scroll', function () { window.requestAnimationFrame(render); }, { passive: true });
  window.addEventListener('resize', render);
  setInterval(render, 1000);
})();

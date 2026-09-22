/* Dependency-free SVG chart. Theme colors are inherited from CSS variables. */
(() => {
  const ns = 'http://www.w3.org/2000/svg';
  const create = (name, attrs, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  document.querySelectorAll('[data-chart]').forEach(host => {
    const points = JSON.parse(host.dataset.chart), svg = host.querySelector('svg');
    const left = 52, right = 697, top = 20, bottom = 260;
    const max = Math.max(10000, Math.ceil(Math.max(...points.map(p => p.value)) / 10000) * 10000);
    for (let i = 0; i <= 4; i++) {
      const y = top + (bottom - top) * i / 4;
      svg.append(create('line', { x1: left, y1: y, x2: right, y2: y, class: 'grid-line' }));
      svg.append(create('text', { x: left - 12, y: y + 4, 'text-anchor': 'end' }, '$' + (max * (4-i) / 4 / 1000).toFixed(0) + 'k'));
    }
    const coords = points.map((point, index) => ({ ...point, x: left + index * (right-left) / Math.max(1, points.length-1), y: bottom - point.value / max * (bottom-top) }));
    const path = coords.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
    svg.append(create('path', { d: `${path} L${right},${bottom} L${left},${bottom} Z`, class: 'area' }));
    svg.append(create('path', { d: path, class: 'line' }));
    coords.forEach(point => {
      svg.append(create('text', { x: point.x, y: 292, 'text-anchor': 'middle' }, point.label));
      const circle = create('circle', { cx: point.x, cy: point.y, r: 4, class: 'chart-point', tabindex: 0, role: 'img', 'aria-label': `${point.label}: $${point.value.toLocaleString()}` });
      circle.append(create('title', {}, `${point.label}: $${point.value.toLocaleString()}`));
      const tip = host.querySelector('.chart-tooltip');
      const show = () => { tip.textContent = `${point.label} · $${point.value.toLocaleString()}`; tip.hidden = false; };
      const hide = () => { tip.hidden = true; };
      circle.addEventListener('mouseenter', show); circle.addEventListener('mouseleave', hide);
      circle.addEventListener('focus', show); circle.addEventListener('blur', hide);
      svg.append(circle);
    });
  });
})();

'use strict';
// Execute repository-owned application source only; JSON fixtures are never evaluated.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
class Node {
  constructor(tag) { this.tag = tag; this.attributes = {}; this.children = []; this.textContent = ''; this.events = {}; }
  setAttribute(key, value) { this.attributes[key] = value; }
  replaceChildren(...nodes) { this.children = nodes; }
  before(node) { this.previous = node; }
  addEventListener(name, callback) { this.events[name] = callback; }
}
function fixture() {
  const nodes = Object.fromEntries(['canvas', 'state', 'action', 'apply', 'reset'].map(id => [id, new Node(id)]));
  let failCreate = false;
  const document = {
    querySelector(selector) { return nodes[selector.slice(1)]; },
    createElement(tag) { return new Node(tag); },
    createElementNS(_namespace, tag) { if (failCreate) throw new Error('synthetic detached-node failure'); return new Node(tag); },
  };
  const context = vm.createContext({document});
  vm.runInContext(source, context, {timeout: 1000});
  function send(action) {
    nodes.action.value = typeof action === 'string' ? action : JSON.stringify(action);
    nodes.apply.events.click();
  }
  function snapshot() {
    const accepted = vm.runInContext('JSON.stringify({elements: [...elements], steps})', context);
    return JSON.stringify({text: nodes.state.textContent, canvas: nodes.canvas.children, accepted});
  }
  return {nodes, context, send, snapshot, fail() { failCreate = true; }};
}
const add = (id = 'wheel', attributes = {cx: 20, cy: 20, r: 10}) => ({type: 'add', id, element: {tag: 'circle', attributes}});
const f = fixture();
f.send(add());
assert.equal(JSON.parse(f.nodes.state.textContent).steps, 1);
f.send({type: 'update', id: 'wheel', changes: {attributes: {cx: 30}, text: '<script>plain text</script>'}});
assert.equal(f.nodes.canvas.children[0].attributes.cx, '30');
assert.equal(f.nodes.canvas.children[0].textContent, '<script>plain text</script>');
assert.equal(f.nodes.canvas.children[0].id, 'pelican-element-wheel');
assert.equal(JSON.parse(f.nodes.state.textContent).steps, 2);
const rejected = [
  null, [], 2, '{', {type: 'undo'}, {type: '__proto__'}, add(), add(''), add('x'.repeat(129)),
  add('x y'), add('__proto__'), {...add('other'), unexpected: true},
  {type: 'delete', id: 'missing'}, {type: 'update', id: 'missing', changes: {}},
  {type: 'add', id: 'x', element: null}, {type: 'add', id: 'x', element: {tag: 'circle', attributes: []}},
  {type: 'add', id: 'x', element: {tag: 'circle', text: 'x'.repeat(4097)}},
  {type: 'add', id: 'x', element: {tag: 'circle', group: 'unsupported'}}, ' '.repeat(32769),
];
for (const tag of ['script', 'foreignObject', 'image', 'use', 'a', 'animate', 'set']) {
  rejected.push({type: 'add', id: 'x', element: {tag}});
  rejected.push({type: 'update', id: 'wheel', changes: {tag}});
}
for (const attribute of ['onload', 'onclick', 'href', 'xlink:href', 'style', 'id', '__proto__']) {
  rejected.push(add('x', {[attribute]: 'https://example.invalid/x'}));
  rejected.push({type: 'update', id: 'wheel', changes: {attributes: {[attribute]: 'unsafe'}}});
}
for (const value of ['url(https://example.invalid)', 'URL (x)', 'u\\72l(x)', 'u/**/rl(x)', 'javascript:1', 'DATA:x', '\u0000', 'x'.repeat(8193), {}, [], null, true]) {
  rejected.push(add('x', {fill: value}));
}
for (const action of rejected) {
  const before = f.snapshot();
  const children = f.nodes.canvas.children;
  f.send(action);
  assert.equal(f.snapshot(), before, JSON.stringify(action).slice(0, 100));
  assert.equal(f.nodes.canvas.children, children);
  assert.notEqual(f.nodes.state.previous.textContent, '');
}
f.send({type: 'delete', id: 'wheel'});
assert.equal(f.nodes.canvas.children.length, 0);
assert.equal(JSON.parse(f.nodes.state.textContent).steps, 3);
f.nodes.reset.events.click();
assert.equal(JSON.parse(f.nodes.state.textContent).steps, 0);
const positive = fixture();
for (const tag of ['g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon']) {
  positive.send({type: 'add', id: `a-${tag}`, element: {tag, attributes: {fill: 'none', stroke: '#123456'}}});
}
assert.equal(positive.nodes.canvas.children.length, 8);
assert.equal(positive.nodes.state.previous.textContent, '');
const beforeFailure = positive.snapshot();
positive.fail();
positive.send(add());
assert.equal(positive.snapshot(), beforeFailure);
assert.match(positive.nodes.state.previous.textContent, /detached-node failure/);
// Trusted sanitized objects avoid quadratic 2000-render fixture setup.
const bounded = fixture();
vm.runInContext("elements = new Map(Array.from({length: LIMITS.elements}, (_, i) => ['x' + i, {tag: 'circle'}])); commit(elements, 2000);", bounded.context);
const beforeLimit = bounded.snapshot();
bounded.send(add('overflow'));
assert.equal(bounded.snapshot(), beforeLimit);
assert.match(bounded.nodes.state.previous.textContent, /element limit/);
console.log(`CANVAS_BROWSER_CONTRACT_OK: ${rejected.length} rejected actions; positive CRUD, reset, bounds and atomic render verified`);

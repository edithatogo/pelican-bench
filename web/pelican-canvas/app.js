'use strict';

// Browser CRUD subset; Python group/undo semantics are not implemented here.
const ALLOWED_TAGS = new Set(['g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon']);
const ALLOWED_ATTRIBUTES = new Set([
  'x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'width', 'height',
  'd', 'points', 'fill', 'stroke', 'stroke-width', 'transform', 'class', 'data-role', 'aria-label',
]);
const LIMITS = Object.freeze({elements: 2000, action: 32768, value: 8192, text: 4096, id: 128});
const canvas = document.querySelector('#canvas');
const state = document.querySelector('#state');
const errorMessage = document.createElement('p');
errorMessage.setAttribute('role', 'alert');
state.before(errorMessage);
let elements = new Map();
let steps = 0;

function object(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('expected an object');
  return value;
}
function fields(value, allowed) {
  object(value);
  if (Object.keys(value).some(key => !allowed.includes(key))) throw new Error('unknown field');
}
function identifier(value) {
  if (typeof value !== 'string' || value.length > LIMITS.id || !/^[A-Za-z][A-Za-z0-9_.:-]*$/.test(value)) {
    throw new Error('invalid or oversized element id');
  }
  return value;
}
function attribute(value) {
  if (!(typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)))) {
    throw new Error('attribute must be a string or finite number');
  }
  const text = String(value);
  // Reject CSS escapes/comments/control bytes as well as literal active values.
  if (text.length > LIMITS.value || /[\\\u0000-\u001f\u007f]|\/\*|url\s*\(|javascript\s*:|data\s*:/i.test(text)) {
    throw new Error('active, external or oversized attribute value');
  }
  return text;
}
function sanitize(value, partial = false) {
  fields(value, ['tag', 'attributes', 'text']);
  const clean = {};
  if (!partial || Object.hasOwn(value, 'tag')) {
    if (!ALLOWED_TAGS.has(value.tag)) throw new Error('unsupported SVG tag');
    clean.tag = value.tag;
  }
  if (Object.hasOwn(value, 'attributes')) {
    object(value.attributes);
    clean.attributes = Object.create(null);
    for (const [key, supplied] of Object.entries(value.attributes)) {
      if (!ALLOWED_ATTRIBUTES.has(key)) throw new Error('unsupported SVG attribute');
      clean.attributes[key] = attribute(supplied);
    }
  }
  if (Object.hasOwn(value, 'text')) {
    if (typeof value.text !== 'string' || value.text.length > LIMITS.text) throw new Error('invalid or oversized text');
    clean.text = value.text;
  }
  return clean;
}
function commit(next, nextSteps) {
  // Construct detached nodes before mutating canvas, accepted map or step counter.
  const ordered = [...next.entries()].sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0);
  const nodes = ordered.map(([id, spec]) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', spec.tag);
    node.id = `pelican-element-${id}`;
    for (const [key, value] of Object.entries(spec.attributes || {})) node.setAttribute(key, value);
    node.textContent = spec.text || '';
    return node;
  });
  const snapshot = JSON.stringify({elements: Object.fromEntries(ordered), steps: nextSteps}, null, 2);
  canvas.replaceChildren(...nodes);
  elements = next;
  steps = nextSteps;
  state.textContent = snapshot;
  errorMessage.textContent = '';
}
function apply(action) {
  object(action);
  const allowed = {add: ['type', 'id', 'element'], update: ['type', 'id', 'changes'], delete: ['type', 'id']};
  if (typeof action.type !== 'string' || !Object.hasOwn(allowed, action.type)) throw new Error('unsupported action');
  fields(action, allowed[action.type]);
  const id = identifier(action.id);
  const next = new Map(elements);
  if (action.type === 'add') {
    if (next.has(id)) throw new Error('duplicate id');
    if (next.size >= LIMITS.elements) throw new Error('element limit exceeded');
    next.set(id, sanitize(action.element));
  } else if (action.type === 'update') {
    if (!next.has(id)) throw new Error('unknown id');
    const old = next.get(id);
    const changes = sanitize(action.changes, true);
    next.set(id, {...old, ...changes, attributes: {...old.attributes, ...changes.attributes}});
  } else if (!next.delete(id)) throw new Error('unknown id');
  commit(next, steps + 1);
}
document.querySelector('#apply').addEventListener('click', () => {
  try {
    const source = document.querySelector('#action').value;
    if (source.length > LIMITS.action) throw new Error('action size limit exceeded');
    apply(JSON.parse(source));
  } catch (error) {
    // Separate alert preserves the last accepted snapshot and canvas on rejection.
    errorMessage.textContent = String(error);
  }
});
document.querySelector('#reset').addEventListener('click', () => commit(new Map(), 0));
commit(new Map(), 0);

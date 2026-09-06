import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

// 서버 렌더링 검사: effect를 실행하지 않으며 실제 제어 클라이언트를 연결하지 않는다.
const require = createRequire(import.meta.url);
const source = readFileSync(new URL('../components/RaspbotRemote.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const exports = {};
new Function('require', 'exports', compiled)((id) => {
  if (id.includes('control-client.mjs')) return { ControlClient: class { constructor() { throw new Error('Hardware client must not start during render'); } } };
  return require(id);
}, exports);
const { RaspbotRemote } = exports;

test('embedded sidebar remote displays its panel immediately, with motion and arming locked', () => {
  const html = renderToStaticMarkup(React.createElement(RaspbotRemote, { embedded: true }));
  assert.match(html, /remote-embedded/);
  assert.match(html, /라즈봇 방향 리모컨/);
  assert.doesNotMatch(html, /class="remote-toggle"/);
  for (const label of ['좌회전', '전진', '우회전', '좌 이동', '우 이동', '후진']) {
    assert.match(html, new RegExp(`aria-label="${label}" disabled=""`));
  }
  assert.match(html, /<button type="button" disabled=""[^>]*>실기모드<\/button>/);
  assert.match(html, /aria-label="정지">/);
});

test('floating variant remains collapsed by default and emergency mode keeps movement disabled', () => {
  const floating = renderToStaticMarkup(React.createElement(RaspbotRemote));
  assert.match(floating, /aria-expanded="false"/);
  assert.doesNotMatch(floating, /라즈봇 방향 리모컨/);
  const locked = renderToStaticMarkup(React.createElement(RaspbotRemote, { embedded: true, emergencyLocked: true }));
  assert.match(locked, /aria-label="전진" disabled=""/);
  assert.match(locked, /<button type="button" disabled=""[^>]*>실기모드<\/button>/);
});

test('sidebar keeps dashboard first, preserves the map, and exposes a separate remote page', () => {
  const shell = readFileSync(new URL('../components/ControlCenter.tsx', import.meta.url), 'utf8');
  const nav = shell.slice(shell.indexOf('const nav:'), shell.indexOf('function AppContent'));
  const keys = [...nav.matchAll(/key: '([^']+)'/g)].map(m => m[1]);
  assert.deepEqual(keys, ['dashboard', 'mapping', 'automatic', 'manual', 'remote', 'vision', 'items', 'history']);
  assert.match(shell, /remote: <section[\s\S]*?<RaspbotRemote embedded emergencyLocked=\{status.emergencyStop\}/);
  assert.match(source, /control\.suspend\(\);\s*client\.current = null;/, 'leaving the page must retain stop/lock cleanup');
  assert.match(source, /window\.removeEventListener\('keydown', handleKeyDown\)/);
});

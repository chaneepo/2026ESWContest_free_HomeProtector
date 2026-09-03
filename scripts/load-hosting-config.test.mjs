import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { loadHostingConfig } from './load-hosting-config.mjs';

function fixture(t, contents) {
  const dir = mkdtempSync(join(tmpdir(), 'carepack-hosting-test-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const file = join(dir, 'hosting.json');
  if (contents !== undefined) writeFileSync(file, contents);
  return { dir, file };
}

test('a missing personal config disables Sites without creating a file', t => {
  const { file } = fixture(t);
  assert.equal(loadHostingConfig(file), null);
  assert.throws(() => readFileSync(file), { code: 'ENOENT' });
});

test('existing bindings remain intact and the source is never rewritten', t => {
  const contents = JSON.stringify({ project_id: 'test-only', d1: 'DB', r2: 'FILES' });
  const { file } = fixture(t, contents);
  assert.deepEqual(loadHostingConfig(pathToFileURL(file)), { d1: 'DB', r2: 'FILES' });
  assert.equal(readFileSync(file, 'utf8'), contents);
});

test('an existing config with no bindings still enables Sites', t => {
  for (const contents of ['{}', '{"project_id":"test-only","d1":null,"r2":null}']) {
    const { file } = fixture(t, contents);
    assert.deepEqual(loadHostingConfig(file), { d1: null, r2: null });
  }
});

test('malformed JSON fails explicitly without exposing the source', t => {
  const { file } = fixture(t, '{"private-value": "test-secret"');
  assert.throws(() => loadHostingConfig(file), error => {
    assert.match(error.message, /JSON/);
    assert.doesNotMatch(error.message, /test-secret/);
    return true;
  });
});

test('non-object configs are rejected instead of silently losing bindings', t => {
  for (const value of ['null', '[]', '42', '"config"', 'true']) {
    const { file } = fixture(t, value);
    assert.throws(() => loadHostingConfig(file), /JSON 객체/);
  }
});

test('invalid binding types and empty binding names are rejected', t => {
  for (const key of ['d1', 'r2']) for (const value of [42, false, [], {}, '', '   ']) {
    const { file } = fixture(t, JSON.stringify({ [key]: value }));
    assert.throws(() => loadHostingConfig(file), new RegExp(key));
  }
});

test('read errors other than missing files are not treated as an empty config', t => {
  const { dir } = fixture(t);
  assert.throws(() => loadHostingConfig(dir), /읽을 수 없습니다/);
});

test('Vite config has no mandatory JSON import and enables Sites conditionally', () => {
  const source = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /import\s+\w+\s+from\s+['"]\.\/.openai\/hosting.json/);
  assert.match(source, /hostingConfig \? \[sites\(\)\] : \[\]/);
  assert.match(source, /hostingConfig \?\? \{ d1: null, r2: null \}/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { ControlClient } from '../web/control-client.mjs';

const status = (extra = {}) => ({ safety_protocol: 2, instance_id: 'one', revision: 1, movement_enabled: false, ...extra });
const response = (body, ok = true) => ({ ok, status: ok ? 200 : 503, json: async () => body });
function setup(handler) {
  const calls = [], views = [];
  const client = new ControlClient('/robot', (view) => views.push(view), async (path, init) => {
    calls.push([path, init]);
    return handler(path, init);
  });
  return { client, calls, views };
}
const armed = () => status({ revision: 2, movement_enabled: true, control_token: 'owner' });

test('status cannot grant ownership; arm requires safety confirmation', async () => {
  const { client, calls, views } = setup(() => response(armed()));
  await client.refresh();
  assert.equal(views.at(-1).movement_enabled, false);
  await client.arm(false);
  await client.motion('move', { action: 'forward' });
  assert.equal(calls.length, 1);
});
test('move and heartbeat include owner token; stop clears it immediately', async () => {
  const { client, calls } = setup((path) => response(path.endsWith('stop') ? status({ revision: 3 }) : armed()));
  await client.refresh();
  await client.arm(true);
  await client.motion('move', { action: 'forward' });
  await client.tick();
  for (const [path, init] of calls.filter(([path]) => /move|heartbeat/.test(path))) {
    assert.equal(JSON.parse(init.body).control_token, 'owner', path);
  }
  const stopping = client.stop();
  assert.equal(client.token, null);
  await stopping;
});
test('old response after STOP cannot re-enable movement', async () => {
  let resolveMove;
  const { client, views } = setup((path) => path.endsWith('move')
    ? new Promise((resolve) => { resolveMove = resolve; })
    : response(path.endsWith('stop') ? status({ revision: 3 }) : armed()));
  await client.refresh(); await client.arm(true);
  const moving = client.motion('move', {});
  await client.stop();
  resolveMove(response(armed()));
  await moving;
  assert.equal(views.at(-1).movement_enabled, false);
});
test('delayed arming response after suspend gets cancelled and STOP retried', async () => {
  let resolveArm;
  const { client, calls } = setup((path) => path.endsWith('mode')
    ? new Promise((resolve) => { resolveArm = resolve; }) : response(status()));
  await client.refresh();
  const arming = client.arm(true);
  client.suspend();
  resolveArm(response(armed()));
  await arming;
  assert.equal(client.token, null);
  assert.ok(calls.filter(([path]) => path.endsWith('stop')).length >= 2);
});
test('HTTP stop failure is never shown as success', async () => {
  const { client, views } = setup(() => response({ error: 'STOP failed' }, false));
  await client.stop();
  assert.equal(views.at(-1).movement_enabled, false);
  assert.match(views.at(-1).message, /STOP failed/);
});
test('heartbeat failure removes permission and requests stop', async () => {
  const { client, calls, views } = setup((path) => {
    if (path.endsWith('heartbeat')) throw new Error('offline');
    return response(armed());
  });
  await client.refresh(); await client.arm(true); await client.tick();
  assert.equal(views.at(-1).movement_enabled, false);
  assert.ok(calls.some(([path]) => path.endsWith('stop')));
});
test('stale server protocol cannot be armed', async () => {
  const { client, calls } = setup(() => response({ movement_enabled: true }));
  await client.refresh(); await client.arm(true);
  assert.equal(client.token, null);
  assert.equal(calls.length, 1);
});
test('double clicks produce only one motion request', async () => {
  let release;
  const { client, calls } = setup((path) => path.endsWith('move')
    ? new Promise((resolve) => { release = resolve; }) : response(armed()));
  await client.refresh(); await client.arm(true);
  const first = client.motion('move', {});
  await client.motion('move', {});
  release(response(armed())); await first;
  assert.equal(calls.filter(([path]) => path.endsWith('move')).length, 1);
});

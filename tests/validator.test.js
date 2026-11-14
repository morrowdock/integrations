import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validate} from '../bin/validate.js';
const root = new URL('../contract/examples/', import.meta.url);
for (const example of JSON.parse(fs.readFileSync(new URL('manifest.json', root)))) {
  test(example.file, () => assert.equal(validate(JSON.parse(fs.readFileSync(new URL(example.file, root)))), example.valid));
}
test('unknown schema rejected', () => assert.equal(validate({schema: 'unknown'}), false));
const fixtures = {
  item: JSON.parse(fs.readFileSync(new URL('valid/material.json', root))),
  request: JSON.parse(fs.readFileSync(new URL('./fixtures/request.json', import.meta.url))),
};
for (const entry of JSON.parse(fs.readFileSync(new URL('./semantic-cases.json', import.meta.url)))) {
  test(`semantic: ${entry.name}`, () => {
    const value = structuredClone(fixtures[entry.base]);
    for (const [path, replacement] of entry.changes) {
      let parent = value;
      for (const key of path.slice(0, -1)) parent = parent[key];
      parent[path.at(-1)] = replacement;
    }
    assert.equal(validate(value), entry.valid);
  });
}

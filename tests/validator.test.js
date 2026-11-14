import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validate} from '../bin/validate.js';
const root = new URL('../contract/examples/', import.meta.url);
for (const example of JSON.parse(fs.readFileSync(new URL('manifest.json', root)))) {
  test(example.file, () => assert.equal(validate(JSON.parse(fs.readFileSync(new URL(example.file, root)))), example.valid));
}
test('unknown schema rejected', () => assert.equal(validate({schema: 'unknown'}), false));

#!/usr/bin/env node
import fs from 'node:fs';
import Ajv2020 from 'ajv/dist/2020.js';
const ajv = new Ajv2020({strict: false, allErrors: true});
const validators = new Map(['item', 'request'].map(kind => {
  const schema = JSON.parse(fs.readFileSync(new URL(`../contract/agent-${kind}.v1.schema.json`, import.meta.url)));
  return [schema.properties.schema.const, ajv.compile(schema)];
}));
export function validate(value) {
  const validator = validators.get(value?.schema);
  return Boolean(validator && validator(value));
}
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(new URL(import.meta.url))) {
  try {
    if (process.argv.length !== 3 || !validate(JSON.parse(fs.readFileSync(process.argv[2])))) throw Error();
    console.log('VALID');
  } catch {
    console.error('INVALID: input does not satisfy the contract');
    process.exitCode = 1;
  }
}

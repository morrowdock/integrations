const zones = new Set(['UTC', ...Intl.supportedValuesOf('timeZone')]);
function validZone(value) {
  if (zones.has(value)) return true;
  // supportedValuesOf lists primary names. ICU also resolves real IANA aliases
  // (for example Etc/UTC), which Python's zoneinfo database accepts too.
  try {
    new Intl.DateTimeFormat('en', {timeZone: value});
    return true;
  } catch { return false; }
}
function validStamp(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|([+-])(\d{2}):(\d{2}))$/.exec(value);
  if (!match) return false;
  const [, year, month, day, hour, minute, second] = match.map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  // Do not use Date.parse: it silently normalizes impossible calendar dates.
  return year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]
    && hour <= 23 && minute <= 59 && second <= 59
    && (match[7] === 'Z' || (Number(match[9]) <= 23 && Number(match[10]) <= 59));
}
function checkFields(value, schema) {
  if (schema.$ref === '#/$defs/dateTime' && !validStamp(value)) return false;
  if (schema.$ref === '#/$defs/timeZone' && !validZone(value)) return false;
  if (Array.isArray(value)) return value.every(child => checkFields(child, schema.items ?? {}));
  if (value && typeof value === 'object') {
    return Object.entries(value).every(([key, child]) => {
      const childSchema = schema.properties?.[key] ?? schema.additionalProperties ?? {};
      return typeof childSchema !== 'object' || checkFields(child, childSchema);
    });
  }
  return true;
}
function resolves(item, pointer) {
  let current = item;
  for (const segment of pointer.split('/').slice(1)) {
    const key = segment.replaceAll('~1', '/').replaceAll('~0', '~');
    if (current === null || typeof current !== 'object' || !Object.hasOwn(current, key)) return false;
    if (Array.isArray(current) && !/^(0|[1-9][0-9]*)$/.test(key)) return false;
    current = current[key];
  }
  return true;
}
export function validateSemantics(value, schema) {
  return checkFields(value, schema)
    && Object.keys(value.verification ?? {}).every(pointer => resolves(value, pointer))
    && (value.status !== 'answered' || value.answeredBy.length > 0);
}

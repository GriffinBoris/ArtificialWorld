function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  return Object.getPrototypeOf(value) === Object.prototype;
}

function normalizeSnakeKeyToCamel(key: string) {
  return key.replace(/[-_]+([a-z0-9])/gi, (_, character: string) => character.toUpperCase());
}

function normalizeCamelKeyToSnake(key: string) {
  return key.replace(/([A-Z])/g, (segment) => `_${segment.toLowerCase()}`).replace(/([a-zA-Z])([0-9]+)/g, "$1_$2");
}

export function snakeToCamel<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => snakeToCamel(item)) as T;
  }

  if (!isPlainObject(value)) {
    return value;
  }

  const nextValue: Record<string, unknown> = {};

  Object.entries(value).forEach(([key, entryValue]) => {
    nextValue[normalizeSnakeKeyToCamel(key)] = snakeToCamel(entryValue);
  });

  return nextValue as T;
}

export function camelToSnake<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => camelToSnake(item)) as T;
  }

  if (!isPlainObject(value)) {
    return value;
  }

  const nextValue: Record<string, unknown> = {};

  Object.entries(value).forEach(([key, entryValue]) => {
    nextValue[normalizeCamelKeyToSnake(key)] = camelToSnake(entryValue);
  });

  return nextValue as T;
}

export function snakeFieldAttrToCamel(attr: string) {
  return normalizeSnakeKeyToCamel(attr);
}

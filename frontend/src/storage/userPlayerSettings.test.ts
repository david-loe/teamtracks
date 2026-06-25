import { afterEach, describe, expect, it } from "vitest";

import { getUserPlayerSettings, saveUserPlayerSettings } from "@/storage/userPlayerSettings";

const originalIndexedDb = globalThis.indexedDB;

afterEach(() => {
  Object.defineProperty(globalThis, "indexedDB", {
    configurable: true,
    value: originalIndexedDb,
  });
});

describe("userPlayerSettings storage", () => {
  it("stores and reads the player settings as one record", async () => {
    const fake = createFakeIndexedDb();
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: fake.factory,
    });

    expect(await getUserPlayerSettings(7)).toBeNull();

    await saveUserPlayerSettings(7, { focusedGainDb: 3, backgroundGainDb: -20 });
    await saveUserPlayerSettings(8, { focusedGainDb: -2, backgroundGainDb: -10 });

    expect(await getUserPlayerSettings(7)).toEqual({ focusedGainDb: 3, backgroundGainDb: -20 });
    expect(await getUserPlayerSettings(8)).toEqual({ focusedGainDb: -2, backgroundGainDb: -10 });
    expect(fake.getStoredValue("organization:7:player")).toEqual({ focusedGainDb: 3, backgroundGainDb: -20 });
  });

  it("reports browsers without IndexedDB support", async () => {
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: undefined,
    });

    await expect(getUserPlayerSettings(7)).rejects.toThrow("IndexedDB wird von diesem Browser nicht unterstützt.");
  });
});

function createFakeIndexedDb() {
  const storedValues = new Map<IDBValidKey, unknown>();
  let storeCreated = false;

  const database = {
    objectStoreNames: {
      contains: () => storeCreated,
    },
    createObjectStore: () => {
      storeCreated = true;
      return {};
    },
    transaction: (_storeName: string, mode: IDBTransactionMode) => {
      const transaction: Record<string, unknown> = {
        error: null,
        oncomplete: null,
        onerror: null,
        onabort: null,
      };
      transaction.objectStore = () => ({
        get: (key: IDBValidKey) => {
          const request: Record<string, unknown> = { result: undefined, error: null, onsuccess: null, onerror: null };
          queueMicrotask(() => {
            request.result = storedValues.get(key);
            (request.onsuccess as (() => void) | null)?.();
          });
          return request;
        },
        put: (value: unknown, key: IDBValidKey) => {
          storedValues.set(key, value);
          queueMicrotask(() => (transaction.oncomplete as (() => void) | null)?.());
          return {};
        },
      });
      if (mode === "readonly") {
        transaction.oncomplete = null;
      }
      return transaction;
    },
    close: () => undefined,
  };

  const factory = {
    open: () => {
      const request: Record<string, unknown> = {
        result: database,
        error: null,
        onupgradeneeded: null,
        onsuccess: null,
        onerror: null,
        onblocked: null,
      };
      queueMicrotask(() => {
        (request.onupgradeneeded as (() => void) | null)?.();
        (request.onsuccess as (() => void) | null)?.();
      });
      return request;
    },
  } as unknown as IDBFactory;

  return {
    factory,
    getStoredValue: (key: IDBValidKey) => storedValues.get(key),
  };
}

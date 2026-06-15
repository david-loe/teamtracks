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

    expect(await getUserPlayerSettings()).toBeNull();

    await saveUserPlayerSettings({ focusedGainDb: 3, backgroundGainDb: -20 });

    expect(await getUserPlayerSettings()).toEqual({ focusedGainDb: 3, backgroundGainDb: -20 });
    expect(fake.getStoredValue()).toEqual({ focusedGainDb: 3, backgroundGainDb: -20 });
  });

  it("reports browsers without IndexedDB support", async () => {
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: undefined,
    });

    await expect(getUserPlayerSettings()).rejects.toThrow("IndexedDB wird von diesem Browser nicht unterstützt.");
  });
});

function createFakeIndexedDb() {
  let storedValue: unknown;
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
        get: () => {
          const request: Record<string, unknown> = { result: undefined, error: null, onsuccess: null, onerror: null };
          queueMicrotask(() => {
            request.result = storedValue;
            (request.onsuccess as (() => void) | null)?.();
          });
          return request;
        },
        put: (value: unknown) => {
          storedValue = value;
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
    getStoredValue: () => storedValue,
  };
}

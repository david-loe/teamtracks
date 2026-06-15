export interface UserPlayerSettings {
  focusedGainDb: number;
  backgroundGainDb: number;
}

export const DEFAULT_USER_PLAYER_SETTINGS: UserPlayerSettings = {
  focusedGainDb: 0,
  backgroundGainDb: -12,
};

const DATABASE_NAME = "teamtracks";
const DATABASE_VERSION = 1;
const STORE_NAME = "user-settings";
const PLAYER_SETTINGS_KEY = "player";

export async function getUserPlayerSettings(): Promise<UserPlayerSettings | null> {
  const database = await openDatabase();
  try {
    return await new Promise<UserPlayerSettings | null>((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, "readonly");
      const request = transaction.objectStore(STORE_NAME).get(PLAYER_SETTINGS_KEY);
      request.onsuccess = () => resolve(isUserPlayerSettings(request.result) ? request.result : null);
      request.onerror = () => reject(request.error ?? new Error("Benutzereinstellungen konnten nicht gelesen werden."));
    });
  } finally {
    database.close();
  }
}

export async function saveUserPlayerSettings(settings: UserPlayerSettings): Promise<void> {
  const database = await openDatabase();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, "readwrite");
      transaction.objectStore(STORE_NAME).put(settings, PLAYER_SETTINGS_KEY);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error ?? new Error("Benutzereinstellungen konnten nicht gespeichert werden."));
      transaction.onabort = () => reject(transaction.error ?? new Error("Speichern der Benutzereinstellungen wurde abgebrochen."));
    });
  } finally {
    database.close();
  }
}

function openDatabase(): Promise<IDBDatabase> {
  if (!globalThis.indexedDB) {
    return Promise.reject(new Error("IndexedDB wird von diesem Browser nicht unterstützt."));
  }

  return new Promise((resolve, reject) => {
    const request = globalThis.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Einstellungsdatenbank konnte nicht geöffnet werden."));
    request.onblocked = () => reject(new Error("Einstellungsdatenbank wird von einem anderen Tab blockiert."));
  });
}

function isUserPlayerSettings(value: unknown): value is UserPlayerSettings {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const settings = value as Partial<UserPlayerSettings>;
  return Number.isFinite(settings.focusedGainDb) && Number.isFinite(settings.backgroundGainDb);
}

const DATABASE = 'household-six-offline-v1';

function openOfflineDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 2);
    request.onupgradeneeded = event => {
      const store = event.oldVersion === 0
        ? request.result.createObjectStore('mutations', { keyPath: 'key' })
        : request.transaction.objectStore('mutations');
      store.createIndex('member', 'userId');
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function transaction(mode, operation) {
  const database = await openOfflineDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = database.transaction('mutations', mode);
      const request = operation(tx.objectStore('mutations'));
      tx.oncomplete = () => resolve(request?.result);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    database.close();
  }
}

export function queuedFor(memberId) {
  return transaction('readonly', store => store.index('member').getAll(memberId));
}

export function storeQueued({ key, userId, itemId, expectedVersion, mutationId, attempt, nextAt }) {
  return transaction('readwrite', store => store.put({
    key, userId, itemId, expectedVersion, mutationId, attempt, nextAt,
  }));
}

export function removeQueued(key) {
  return transaction('readwrite', store => store.delete(key));
}

export async function clearQueued(memberId) {
  await transaction('readwrite', store => {
    const request = store.index('member').openCursor(memberId);
    request.onsuccess = () => {
      const cursor = request.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      }
    };
  });
}

export function clearLegacyCaches() {
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i);
    if (key?.startsWith('hs-cache-') || key?.startsWith('hs-queue-')) localStorage.removeItem(key);
  }
}

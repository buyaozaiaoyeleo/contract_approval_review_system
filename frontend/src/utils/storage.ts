const PREFIX = 'contract_review'

export function getStorage(key: string): string | null {
  return localStorage.getItem(`${PREFIX}_${key}`)
}

export function setStorage(key: string, value: string): void {
  localStorage.setItem(`${PREFIX}_${key}`, value)
}

export function removeStorage(key: string): void {
  localStorage.removeItem(`${PREFIX}_${key}`)
}

export function getJSON<T = unknown>(key: string): T | null {
  const value = getStorage(key)
  if (!value) return null
  try {
    return JSON.parse(value) as T
  } catch {
    return null
  }
}

export function setJSON(key: string, value: unknown): void {
  setStorage(key, JSON.stringify(value))
}

export function clearAll(): void {
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(PREFIX)) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key))
}
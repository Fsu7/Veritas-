const RECENT_SEARCHES_KEY = 'recent_searches'

export function getRecentSearches(): string[] {
  try {
    const data = localStorage.getItem(RECENT_SEARCHES_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export function saveRecentSearch(query: string): void {
  const list = getRecentSearches()
  const index = list.indexOf(query)
  if (index >= 0) {
    list.splice(index, 1)
  }
  list.unshift(query)
  if (list.length > 10) {
    list.length = 10
  }
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(list))
}

export function clearRecentSearches(): void {
  localStorage.removeItem(RECENT_SEARCHES_KEY)
}

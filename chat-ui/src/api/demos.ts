export interface DemoItem {
  title: string
  question: string
  answer: string
}

export async function fetchDemos(): Promise<DemoItem[]> {
  try {
    const resp = await fetch('/demos/')
    if (!resp.ok) return []
    return resp.json()
  } catch {
    return []
  }
}

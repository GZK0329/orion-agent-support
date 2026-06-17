export interface FileItem {
  filename: string
  size: number
  updated_at: string
}

export async function fetchDocuments(adminToken: string): Promise<FileItem[]> {
  const resp = await fetch('/documents/', {
    headers: { 'X-Admin-Token': adminToken },
  })
  if (!resp.ok) return []
  return resp.json()
}

export async function uploadDocument(
  file: File,
  adminToken: string,
  onProgress?: (pct: number) => void,
): Promise<string> {
  const form = new FormData()
  form.append('file', file)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/documents/upload')
    xhr.setRequestHeader('X-Admin-Token', adminToken)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status === 201) {
        const data = JSON.parse(xhr.responseText)
        resolve(data.message || '导入成功')
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.detail || `上传失败 (${xhr.status})`))
        } catch {
          reject(new Error(`上传失败 (${xhr.status})`))
        }
      }
    }

    xhr.onerror = () => reject(new Error('网络错误'))
    xhr.send(form)
  })
}

export async function deleteDocument(filename: string, adminToken: string): Promise<boolean> {
  const resp = await fetch(`/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
    headers: { 'X-Admin-Token': adminToken },
  })
  return resp.ok
}

export async function reindexDocuments(adminToken: string): Promise<string> {
  const resp = await fetch('/documents/reindex', {
    method: 'POST',
    headers: { 'X-Admin-Token': adminToken },
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || '重建失败')
  }
  const data = await resp.json()
  return data.message
}

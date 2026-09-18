import { useState } from 'react'
import { uploadHar } from '../api/har'
import { ApiError } from '../api/client'
import type { UploadResponse } from '../api/types'

interface FileUploadProps {
  onUploaded: (upload: UploadResponse) => void
}

/** Replaces st.file_uploader: pick a .har file, upload it once, hand the
 * resulting upload_id up to the app shell. */
export function FileUpload({ onUploaded }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setIsUploading(true)
    setError(null)
    try {
      const result = await uploadHar(file)
      onUploaded(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="file-upload">
      <label className="file-upload__dropzone">
        <input
          type="file"
          accept=".har,application/json"
          disabled={isUploading}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
          }}
        />
        {isUploading ? 'Uploading...' : 'Upload your HTTP Archive document (.har)'}
      </label>
      {error && <p className="file-upload__error">{error}</p>}
    </div>
  )
}

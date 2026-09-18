import { useState } from 'react'
import { uploadHar } from '../api/har'
import { ApiError } from '../api/client'
import type { UploadResponse } from '../api/types'

interface FileUploadProps {
  onUploaded: (upload: UploadResponse) => void
  onCancel?: () => void
  /** Smaller dropzone for the "switch file" panel, vs. the full-page initial
   * upload screen. */
  compact?: boolean
}

/**
 * Replaces st.file_uploader: pick a .har file, upload it once, hand the
 * resulting upload_id up to the app shell.
 *
 * Single-file today by design -- one <input> and one uploadHar(file) call.
 * A future "load multiple HARs / a whole folder" feature would add a
 * batch variant of this (e.g. a `multiple`/`webkitdirectory` input plus a
 * loop calling the same uploadHar), not change how this one works, so
 * there's no premature multi-file plumbing here yet.
 */
export function FileUpload({ onUploaded, onCancel, compact = false }: FileUploadProps) {
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
    <div className={`file-upload ${compact ? 'file-upload--compact' : ''}`}>
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
      {onCancel && (
        <button className="file-upload__cancel" onClick={onCancel} disabled={isUploading}>
          Cancel
        </button>
      )}
    </div>
  )
}

import { useState } from 'react'
import { uploadHar } from '../api/har'
import { ApiError } from '../api/client'
import type { UploadResponse } from '../api/types'
import { Button } from './Button'

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
    <div className={compact ? 'mb-2 flex items-center gap-3' : ''}>
      <label
        className={`block cursor-pointer rounded-lg border-2 border-dashed border-border text-text-muted transition-colors hover:border-accent hover:text-text ${
          compact ? 'rounded-md px-5 py-3' : 'p-16 text-center'
        }`}
      >
        <input
          type="file"
          accept=".har,application/json"
          disabled={isUploading}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
          }}
        />
        {isUploading ? (
          'Uploading…'
        ) : compact ? (
          'Upload your HTTP Archive document (.har)'
        ) : (
          <span className="flex flex-col items-center gap-1.5">
            <span className="text-sm font-medium">Upload your HTTP Archive document</span>
            <span className="font-mono text-xs">.har</span>
          </span>
        )}
      </label>
      {error && <p className="text-error">{error}</p>}
      {onCancel && (
        <Button onClick={onCancel} disabled={isUploading}>
          Cancel
        </Button>
      )}
    </div>
  )
}

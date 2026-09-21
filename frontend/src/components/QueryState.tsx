interface LoadingStateProps {
  label?: string
}

export function LoadingState({ label = 'Loading...' }: LoadingStateProps) {
  return <p className="text-sm text-text-muted">{label}</p>
}

interface ErrorStateProps {
  label: string
}

export function ErrorState({ label }: ErrorStateProps) {
  return <p className="text-sm text-error">{label}</p>
}

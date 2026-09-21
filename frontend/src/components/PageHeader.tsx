interface PageHeaderProps {
  title: string
}

export function PageHeader({ title }: PageHeaderProps) {
  return (
    <div className="mb-1 flex items-center gap-2.5 border-b border-border pb-3">
      <img src="/har_analyzer.png" alt="" className="h-7 w-7" />
      <h1 className="m-0 text-[19px] font-semibold tracking-tight">{title}</h1>
    </div>
  )
}

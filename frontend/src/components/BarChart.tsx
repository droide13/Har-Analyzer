import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'

const getAccentColor = () => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()

/** Tracks the `--accent` custom property so chart bars follow the OS
 * dark/light switch the same way every CSS-styled element already does --
 * ECharts takes a literal color, not a var(), so this is the one place
 * that needs to read it in JS. */
function useAccentColor(): string {
  const [accent, setAccent] = useState(getAccentColor)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setAccent(getAccentColor())
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return accent
}

export interface BarChartDatum {
  label: string
  value: number
}

interface BarChartProps {
  data: BarChartDatum[]
  orientation?: 'vertical' | 'horizontal'
  valueLabel?: string
  heightPx?: number
}

/**
 * Small, generic ECharts bar chart -- the one chart shape this phase needs
 * (method/status distribution, top-domains), used three times within
 * Overview alone, so it earns being a shared component from the start.
 * Not meant to grow into a general charting kit; new visualization shapes
 * (e.g. Dissemination's timeline) get their own component when that phase
 * lands, rather than this one sprouting options for cases it doesn't serve.
 */
export function BarChart({ data, orientation = 'vertical', valueLabel = 'Value', heightPx }: BarChartProps) {
  const accent = useAccentColor()
  const labels = data.map((d) => d.label)
  const values = data.map((d) => d.value)
  const isHorizontal = orientation === 'horizontal'

  const option = {
    grid: { containLabel: true, left: 8, right: 16, top: 24, bottom: 8 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: isHorizontal ? { type: 'value', name: valueLabel } : { type: 'category', data: labels },
    yAxis: isHorizontal ? { type: 'category', data: labels } : { type: 'value', name: valueLabel },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: { color: accent },
      },
    ],
  }

  const height = heightPx ?? (isHorizontal ? Math.max(160, 40 + data.length * 28) : 260)

  return <ReactECharts option={option} style={{ height }} notMerge />
}

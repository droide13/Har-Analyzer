import ReactECharts from 'echarts-for-react'

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
        itemStyle: { color: '#6b3bff' },
      },
    ],
  }

  const height = heightPx ?? (isHorizontal ? Math.max(160, 40 + data.length * 28) : 260)

  return <ReactECharts option={option} style={{ height }} notMerge />
}

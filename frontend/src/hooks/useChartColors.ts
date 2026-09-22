import { useEffect, useState } from 'react'

export interface ChartColors {
  accent: string
  text: string
  textMuted: string
  border: string
  bgSubtle: string
  ok: string
}

function readChartColors(): ChartColors {
  const style = getComputedStyle(document.documentElement)
  const get = (name: string) => style.getPropertyValue(name).trim()
  return {
    accent: get('--color-accent'),
    text: get('--color-text'),
    textMuted: get('--color-text-muted'),
    border: get('--color-border'),
    bgSubtle: get('--color-bg-subtle'),
    ok: get('--color-ok'),
  }
}

/** Tracks theme-driven custom properties so charts follow the OS dark/light
 * switch the same way every CSS-styled element already does -- ECharts
 * takes literal colors, not var(), so this is the one place that needs to
 * read them in JS. Without this, ECharts' own default (near-black) axis
 * label/line colors are illegible against the dark theme's background. */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState(readChartColors)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setColors(readChartColors())
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return colors
}

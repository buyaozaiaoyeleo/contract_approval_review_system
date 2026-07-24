import dayjs from 'dayjs'
import { DATE_FORMAT, DATETIME_FORMAT } from './constants'

export function formatDate(date: string | Date | number, format = DATE_FORMAT): string {
  if (!date) return '-'
  return dayjs(date).format(format)
}

export function formatDateTime(date: string | Date | number): string {
  return formatDate(date, DATETIME_FORMAT)
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60)
    const s = (seconds % 60).toFixed(1)
    return `${m}m ${s}s`
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function formatAmount(amount: number): string {
  return amount.toLocaleString('zh-CN', {
    style: 'currency',
    currency: 'CNY',
  })
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}
// 时区与时间格式化工具。约定内部统一 UTC（unix 秒），UI 按所选时区展示。

export function tzToOffsetMinutes(tz: string): number {
  // 支持 "UTC", "UTC+08:00", "UTC-05:30" 等固定偏移
  if (tz === 'UTC') return 0
  const m = tz.match(/^UTC([+-])(\d{1,2}):(\d{2})$/)
  if (!m) return 0
  const sign = m[1] === '-' ? -1 : 1
  return sign * (parseInt(m[2], 10) * 60 + parseInt(m[3], 10))
}

function pad(n: number): string {
  return n < 10 ? '0' + n : String(n)
}

export function formatInTz(unix: number, tz: string): { date: string; time: string; weekday: string } {
  const offMin = tzToOffsetMinutes(tz)
  const d = new Date((unix + offMin * 60) * 1000)
  const date = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`
  const time = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
  const weekday = ['日', '一', '二', '三', '四', '五', '六'][d.getUTCDay()]
  return { date, time, weekday }
}

export function toUtcUnix(dateStr: string, timeStr: string, tz: string): number {
  const offMin = tzToOffsetMinutes(tz)
  const [y, mo, d] = dateStr.split('-').map((x) => parseInt(x, 10))
  const [h, mi, s] = timeStr.split(':').map((x) => parseInt(x, 10))
  const local = Date.UTC(y, mo - 1, d, h, mi, s || 0)
  return Math.floor(local / 1000 - offMin * 60)
}

export function nowUtcUnix(): number {
  return Math.floor(Date.now() / 1000)
}

// 将 unix 秒对齐到当天 00:00（按给定时区）
export function startOfDayInTz(unix: number, tz: string): number {
  const { date } = formatInTz(unix, tz)
  return toUtcUnix(date, '00:00:00', tz)
}

// 一天内的秒偏移（0..86400），用于时间轴滑块
export function secondsIntoDay(unix: number, tz: string): number {
  const offMin = tzToOffsetMinutes(tz)
  const local = (unix + offMin * 60) % 86400
  return ((local % 86400) + 86400) % 86400
}

export function fromDayOffset(dayStartUnix: number, offsetSec: number): number {
  return dayStartUnix + offsetSec
}

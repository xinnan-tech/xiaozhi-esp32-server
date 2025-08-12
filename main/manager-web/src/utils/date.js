export const toDate = (date) => {
  return isDate(date) ? new Date(date) : null
}

export const isDate = (date) => {
  if (date === null || date === undefined) return false
  if (isNaN(new Date(date).getTime())) return false
  return true
}

export const isDateObject = (val) => {
  return val instanceof Date
}

export const formatAddDate = (date, format, addDay) => {
  date = toDate(date)
  if (!date) {
    return ''
  }
  if (!addDay) {
    date.setDate(date.getDate() + addDay)
  }
  return formatDateTool(date, format || 'yyyy-MM-dd HH:mm:ss')
}

export const formatDate = (date, format) => {
  date = toDate(date)
  if (!date) return ''
  return formatDateTool(date, format || 'yyyy-MM-dd HH:mm:ss')
}

function formatDateTool(date, fmt) {
  if (/(y+)/.test(fmt)) {
    fmt = fmt.replace(
      RegExp.$1,
      (date.getFullYear() + '').substr(4 - RegExp.$1.length)
    )
  }
  const o = {
    'M+': date.getMonth() + 1,
    'd+': date.getDate(),
    'h+': date.getHours(),
    'm+': date.getMinutes(),
    's+': date.getSeconds()
  }
  for (const k in o) {
    if (new RegExp(`(${k})`).test(fmt)) {
      const str = o[k] + ''
      fmt = fmt.replace(
        RegExp.$1,
        RegExp.$1.length === 1 ? str : padLeftZero(str)
      )
    }
  }
  return fmt
}

function padLeftZero(str) {
  return ('00' + str).substr(str.length)
}

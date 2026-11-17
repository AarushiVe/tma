export function fmtDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso.replace(' ', 'T') + 'Z')
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function money(n) {
  return '₹' + Number(n || 0).toLocaleString('en-IN')
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

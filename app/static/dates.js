export function householdDate(timezone) {
  const format = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' });
  const parts = Object.fromEntries(format.formatToParts(new Date()).map(({ type, value }) => [type, value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function asDate(day) {
  return new Date(`${day}T12:00:00Z`);
}

export function shiftDay(day, amount) {
  const date = asDate(day);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function shiftMonth(day, amount) {
  const date = asDate(day);
  date.setUTCDate(1);
  date.setUTCMonth(date.getUTCMonth() + amount);
  return date.toISOString().slice(0, 10);
}

export function weekday(day) {
  return asDate(day).getUTCDay();
}

export function formatDay(day, options) {
  return new Intl.DateTimeFormat(undefined, { ...options, timeZone: 'UTC' }).format(asDate(day));
}

export function formatClock(local) {
  if (!local || local.length < 16) return '';
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
    .format(new Date(`${local.slice(0, 16)}:00Z`));
}

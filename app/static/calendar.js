import { escapeHtml as h } from './html.js';
import { formatClock, formatDay, shiftDay, shiftMonth, weekday } from './dates.js';

export const CALENDAR_VIEWS = ['month', 'week', 'day', 'agenda'];
export const COLOR_NAMES = {
  '#233C32': 'forest', '#78937D': 'sage', '#C69A5D': 'gold',
  '#54768C': 'blue', '#9B6B72': 'rose', '#7B6C9B': 'violet',
};

export function rangeFor({ anchor, view }) {
  if (view === 'month') {
    const first = shiftMonth(anchor, 0);
    const start = shiftDay(first, -weekday(first));
    return { start, end: shiftDay(start, 42) };
  }
  if (view === 'week') {
    const start = shiftDay(anchor, -weekday(anchor));
    return { start, end: shiftDay(start, 7) };
  }
  return { start: anchor, end: shiftDay(anchor, view === 'agenda' ? 30 : 1) };
}

export function moveCalendar({ anchor, view }, direction) {
  if (view === 'month') return shiftMonth(anchor, direction);
  return shiftDay(anchor, direction * (view === 'week' ? 7 : view === 'agenda' ? 30 : 1));
}

function eventDates(event) {
  const start = event.occurrenceStart;
  const end = event.occurrenceEnd;
  const exclusive = event.allDay || end.slice(11, 19) === '00:00:00';
  return [start.slice(0, 10), exclusive ? shiftDay(end.slice(0, 10), -1) : end.slice(0, 10)];
}

export function calendarEvent(event, canEdit, compact = false, day = event.occurrenceStart?.slice(0, 10)) {
  const firstDay = event.occurrenceStart?.slice(0, 10);
  const clock = event.allDay ? 'All day'
    : firstDay === day ? formatClock(event.occurrenceStart) : 'Continues';
  const end = event.occurrenceEnd?.slice(0, 10) === day ? formatClock(event.occurrenceEnd) : '';
  const color = COLOR_NAMES[event.memberColor] || 'sage';
  const text = `<span class="calendar-event-title">${h(event.title)}</span>
    ${compact ? '' : `<span class="item-detail">${h([clock, end && !event.allDay ? `to ${end}` : '', event.memberName].filter(Boolean).join(' '))}</span>
    ${event.details ? `<span class="item-detail">${h(event.details)}</span>` : ''}`}`;
  const style = `calendar-event calendar-color-${color}${compact ? ' calendar-event-compact' : ''}`;
  return canEdit
    ? `<button type="button" class="${style}" data-calendar-edit="${h(event.id)}" data-calendar-occurrence="${h(firstDay)}">${text}</button>`
    : `<div class="${style}">${text}</div>`;
}

function byDay(events, day) {
  return events.filter(event => {
    const [first, last] = eventDates(event);
    return day >= first && day <= last;
  });
}

export function calendarView(data, state, members, canEdit) {
  const { anchor, view, member } = state;
  const { start, end } = rangeFor(state);
  const today = data?.today;
  const events = data?.events || [];
  let heading = formatDay(anchor, { month: 'long', year: 'numeric' });
  if (view === 'day') heading = formatDay(anchor, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  if (view === 'week' || view === 'agenda') heading = `${formatDay(start, { month: 'short', day: 'numeric' })} – ${formatDay(shiftDay(end, -1), { month: 'short', day: 'numeric', year: 'numeric' })}`;

  const days = [];
  for (let day = start; day < end; day = shiftDay(day, 1)) {
    const entries = byDay(events, day);
    if (view === 'agenda' && entries.length === 0) continue;
    if (view === 'month') {
      const label = formatDay(day, { month: 'long', day: 'numeric' });
      days.push(`<div class="calendar-cell ${day.slice(0, 7) !== anchor.slice(0, 7) ? 'calendar-outside' : ''}">
        <button class="calendar-date ${day === today ? 'calendar-current' : ''}" data-calendar-day="${day}"
          aria-label="${h(label)}${entries.length ? `, ${entries.length} events` : ''}">${Number(day.slice(-2))}</button>
        ${entries.slice(0, 3).map(event => calendarEvent(event, canEdit, true, day)).join('')}
        ${entries.length > 3 ? `<button class="calendar-more" data-calendar-day="${day}">+${entries.length - 3}</button>` : ''}
      </div>`);
    } else {
      const label = formatDay(day, { weekday: 'long', month: 'short', day: 'numeric' });
      days.push(`<section class="calendar-day-group">
        ${view !== 'day' ? `<h3><button class="text-button" data-calendar-day="${day}">${h(label)}</button></h3>` : ''}
        ${entries.length ? entries.map(event => calendarEvent(event, canEdit, false, day)).join('') : '<p class="subtle">No events</p>'}
      </section>`);
    }
  }
  const options = members.filter(entry => entry.role !== 'display').map(entry =>
    `<option value="${h(entry.id)}" ${entry.id === member ? 'selected' : ''}>${h(entry.display_name)}</option>`).join('');
  return `<header class="greeting"><div><h1>Calendar</h1><p class="subtle">${h(data?.timezone || '')}</p></div>
    ${canEdit ? '<button class="primary" data-calendar-new>New event</button>' : ''}
  </header>
  <div class="calendar-controls">
    <div class="calendar-views" aria-label="Calendar view">${CALENDAR_VIEWS.map(value =>
      `<button class="chip ${value === view ? 'active' : ''}" aria-pressed="${value === view}" data-calendar-view="${value}">${value}</button>`).join('')}</div>
    <label class="field">Show member<select id="calendar-member"><option value="">Everyone</option>${options}</select></label>
  </div>
  <div class="calendar-controls calendar-navigation">
    <h2>${h(heading)}</h2>
    <div class="actions">
      <button class="secondary" data-calendar-step="-1" aria-label="Previous ${view}">‹</button>
      <button class="secondary" data-calendar-today>Today</button>
      <button class="secondary" data-calendar-step="1" aria-label="Next ${view}">›</button>
    </div>
  </div>
  ${!data ? '<p class="subtle">Connect to load the calendar.</p>' : ''}
  ${view === 'month' ? `<div class="calendar-month" aria-label="Month grid">
    ${['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(name => `<span class="calendar-weekday">${name}</span>`).join('')}
    ${days.join('')}
  </div>` : `<div class="calendar-${view}">${days.join('') || '<p class="empty">No events in this date range.</p>'}</div>`}
  ${view === 'agenda' && data?.unscheduled.length ? `<section class="calendar-day-group">
    <h3>Unscheduled</h3>${data.unscheduled.map(event => calendarEvent(event, canEdit)).join('')}</section>` : ''}
  <div class="calendar-controls calendar-exchange">
    <a href="/api/calendar/export" download>Export iCalendar</a>
    ${canEdit ? `<form id="calendar-import" class="actions">
      <label class="field">iCalendar file<input type="file" name="ics" accept=".ics,text/calendar" required></label>
      <button class="secondary">Import</button>
    </form>` : ''}
  </div>`;
}

export function calendarForm(event, memberList, day, skippedDay, allDay) {
  const input = allDay ? 'date' : 'datetime-local';
  const defaultStart = allDay ? day : `${day}T09:00`;
  const defaultEnd = allDay ? shiftDay(day, 1) : `${day}T10:00`;
  const format = (value, fallback) => {
    if (!value) return fallback;
    if (allDay) return value.slice(0, 10);
    return value.length > 10 ? value.slice(0, 16) : `${value}T09:00`;
  };
  const repeat = event?.rule?.startsWith('FREQ=') && !event.rule.includes(';')
    ? event.rule.slice(5).toLowerCase() : event?.rule ? 'imported' : '';
  const choices = [['', 'No repeat'], ['daily', 'Daily'], ['weekly', 'Weekly'], ['monthly', 'Monthly'], ['yearly', 'Yearly']];
  if (repeat === 'imported') choices.push(['imported', 'Imported recurrence rule']);
  return `<header class="greeting"><h1>${event?.id ? 'Edit calendar event' : 'New calendar event'}</h1></header>
  <form id="calendar-event-form" class="card form form-card">
    <label class="field">Event title<input name="title" maxlength="120" value="${h(event?.title)}" required></label>
    <label class="field">Notes<textarea name="details" maxlength="1000">${h(event?.details)}</textarea></label>
    <label class="calendar-checkbox"><input type="checkbox" name="allDay" ${allDay ? 'checked' : ''}> All-day event</label>
    <label class="field">Start<input type="${input}" name="start" value="${h(format(event?.start, defaultStart))}" required></label>
    <label class="field">${allDay ? 'End date (exclusive)' : 'End'}<input type="${input}" name="end" value="${h(format(event?.end, defaultEnd))}" required></label>
    <label class="field">Member<select name="assignedTo"><option value="">Whole household</option>
      ${memberList.filter(member => member.role !== 'display').map(member =>
        `<option value="${h(member.id)}" ${member.id === event?.assignedTo ? 'selected' : ''}>${h(member.display_name)}</option>`).join('')}</select></label>
    <label class="field">Repeat<select name="repeat">
      ${choices.map(([value, label]) => `<option value="${value}" ${repeat === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
    <label class="field">Skip dates (YYYY-MM-DD, separated by commas)
      <input name="exceptions" value="${h(event?.exceptions?.join(', '))}" placeholder="2026-12-25"></label>
    <div class="actions">
      <button class="primary">Save event</button>
      <button class="secondary" type="button" data-calendar-cancel>Cancel</button>
      ${event?.id ? '<button class="secondary danger" type="button" data-calendar-delete>Delete event</button>' : ''}
      ${event?.id && event.rule && skippedDay ? `<button class="secondary" type="button" data-calendar-skip="${h(skippedDay)}">Skip this occurrence</button>` : ''}
    </div>
  </form>`;
}

import { calendarEvent } from './calendar.js';
import { formatDay } from './dates.js';
import { escapeHtml as h } from './html.js';

export function dashboardView(data, household, canAdd, renderTask, renderBalances) {
  const date = data ? formatDay(data.date, { weekday: 'long', month: 'long', day: 'numeric' }) : '';
  const header = `<header class="greeting"><div><p class="eyebrow">${h(household)}${date ? ` · ${h(date)}` : ''}</p>
    <h1>Today</h1></div>${canAdd ? '<button class="secondary" data-action="add">＋ Add</button>' : ''}</header>`;
  if (!data) return `${header}<p class="empty">Connect to load your household’s schedule.</p>`;
  const section = (label, nav, rows, render, empty) => `<section>
    <div class="section-head"><h2>${label}</h2>
    <button class="text-button" data-nav="${nav}">${({ calendar: 'Calendar', tasks: 'Chores', meals: 'Meal plan', shopping: 'Lists', rewards: 'Rewards' })[nav]} →</button></div>
    ${rows.length ? `<div class="list">${rows.map(render).join('')}</div>` : `<p class="empty">${empty}</p>`}
  </section>`;
  const renderUpcoming = event => {
    const day = event.occurrenceStart.slice(0, 10);
    return `<div><div class="subtle">${formatDay(day, { weekday: 'short', month: 'short', day: 'numeric' })}</div>
      ${calendarEvent(event, false)}</div>`;
  };
  return `${header}<div class="dashboard-columns">
    <div>
      ${section('Today’s appointments', 'calendar', data.appointments, event => calendarEvent(event, false, false, data.date), 'No appointments today.')}
      ${section('Upcoming events', 'calendar', data.upcoming, renderUpcoming, 'No upcoming events this week.')}
      ${section('Planned meals', 'meals', data.meals, renderTask, 'No meals planned today.')}
    </div>
    <div>
      ${section('Today’s chores', 'tasks', data.chores, renderTask, 'No chores due today.')}
      ${data.overdue.length ? section('Overdue chores', 'tasks', data.overdue, renderTask, '') : ''}
      ${data.unscheduled.length ? section('Chores without a due date', 'tasks', data.unscheduled, renderTask, '') : ''}
      ${section('Shopping summary', 'shopping', data.shopping, list =>
        `<button class="card row dashboard-shopping" data-dashboard-list="${h(list.id)}">${h(list.name)} <strong>${list.open} to get</strong></button>`, 'No items on the shopping lists.')}
      <section>
        <div class="section-head"><h2>Reward balances</h2><button class="text-button" data-nav="rewards">Rewards →</button></div>
        ${renderBalances(data.balances)}
      </section>
    </div>
  </div>`;
}

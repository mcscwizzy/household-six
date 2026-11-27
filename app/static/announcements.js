import { escapeHtml as h } from './html.js';

export function announcementsView(data, role, expired) {
  const adult = ['owner','admin','adult'].includes(role);
  return `<header class="greeting"><h1>Announcements</h1>
    ${adult ? '<button class="primary" data-domain-open="announcement">New announcement</button>' : ''}
  </header>
  ${adult ? `<button type="button" class="secondary" data-announcement-expired aria-pressed="${expired}">${expired ? 'Hide expired' : 'Show expired'}</button>` : ''}
  <div class="list announcement-list">${data?.items.length ? data.items.map(item => {
    const isExpired = item.expires_on && item.expires_on < data.date;
    return `<article class="card domain-row">
      <div class="actions"><h2>${h(item.title)}</h2>${item.pinned ? '<span class="badge">Pinned</span>' : ''}
        ${isExpired ? '<span class="badge">Expired</span>' : ''}</div>
      <p>${h(item.details)}</p>
      <p class="item-detail">${item.expires_on ? `Through ${h(item.expires_on)}` : ''}${adult ? ` · ${item.ackCount} acknowledged` : ''}</p>
      <div class="actions">
        ${role !== 'display' && !isExpired ? `<button class="secondary" data-announcement-ack="${h(item.id)}" ${item.acknowledged ? 'disabled' : ''}
          aria-label="Acknowledge ${h(item.title)}">${item.acknowledged ? 'Acknowledged' : 'Acknowledge'}</button>` : ''}
        ${adult ? `<button class="text-button" data-announcement-edit="${h(item.id)}">Edit</button>` : ''}
      </div>
    </article>`;
  }).join('') : '<p class="empty">No announcements.</p>'}</div>`;
}

export function announcementForm(item) {
  return `<header class="greeting"><h1>${item ? 'Edit announcement' : 'New announcement'}</h1></header>
    <form class="card form form-card" id="announcement-form">
      <label class="field">Title<input name="title" maxlength="120" value="${h(item?.title)}" required></label>
      <label class="field">Message<textarea name="details" maxlength="1000" required>${h(item?.details)}</textarea></label>
      <label class="field">Keep visible through<input name="expiresOn" type="date" value="${h(item?.expires_on)}"></label>
      <label class="calendar-checkbox"><input name="pinned" type="checkbox" ${item?.pinned ? 'checked' : ''}> Pin to household display</label>
      <div class="actions"><button class="primary">Publish announcement</button>
        <button class="secondary" type="button" data-nav="announcements">Cancel</button>
        ${item ? '<button type="button" class="secondary danger" data-announcement-archive>Archive</button>' : ''}</div>
    </form>`;
}

export function wallView(dashboard, data, household, timezone) {
  const now = new Intl.DateTimeFormat(undefined, { timeZone: timezone, hour: 'numeric', minute: '2-digit',
    weekday: 'long', month: 'long', day: 'numeric' }).format(new Date());
  const section = (heading, entries) => `<section class="card wall-card"><h2>${heading}</h2>
    ${entries.length ? `<ul>${entries.map(item => `<li><strong>${h(item.title)}</strong>
      ${item.details ? `<p>${h(item.details)}</p>` : ''}</li>`).join('')}</ul>` : '<p class="subtle">Nothing scheduled</p>'}</section>`;
  return `<main class="wall"><header class="wall-head"><div><p class="eyebrow">${h(household)}</p>
    <h1>${h(now)}</h1></div>
    <div class="actions"><button class="secondary" data-wall-fullscreen>Full screen</button>
    <button class="secondary" data-nav="today">Exit display</button></div></header>
    <div class="wall-grid">
      ${section('Appointments', dashboard?.appointments || [])}
      ${section('Chores', [...(dashboard?.scheduledChores || []).filter(item => item.status === 'open'), ...(dashboard?.chores || []).filter(item => !item.completed)])}
      ${section('Meals', dashboard?.meals || [])}
      ${section('Pinned announcements', data?.items.filter(item => item.pinned) || [])}
    </div>
  </main>`;
}

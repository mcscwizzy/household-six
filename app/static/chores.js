import { formatDay } from './dates.js';
import { escapeHtml as h } from './html.js';

const ROUTINES = { morning: 'Morning routine', anytime: 'Anytime', bedtime: 'Bedtime routine' };
const STATUS = { pending: 'Waiting for approval', approved: 'Completed', declined: 'Try again' };
export function choreCard(item, canComplete) {
  const ready = ['open', 'declined'].includes(item.status);
  return `<article class="card row item-card chore-card">
    ${ready && canComplete ? `<button class="check" data-chore-complete="${h(item.id)}" aria-label="Check off ${h(item.title)}"></button>` : ''}
    <div class="item-main"><div class="item-title">${h(item.title)}</div>
      <div class="item-detail">${h([item.memberName || 'Shared', item.details].filter(Boolean).join(' · '))}</div>
      ${item.status !== 'open' ? `<span class="badge">${STATUS[item.status]}</span>` : ''}
    </div>
    ${item.points ? `<strong class="badge">${item.points} pts</strong>` : ''}
  </article>`;
}

export function choresView(data, day, today, role, legacy, renderTask) {
  const adult = ['owner', 'admin', 'adult'].includes(role);
  const sections = Object.entries(ROUTINES).flatMap(([routine, name]) => {
    const entries = data?.scheduled.filter(item => item.routine === routine) || [];
    return entries.length ? [`<section><div class="section-head"><h2>${name}</h2></div>
      <div class="list">${entries.map(item => choreCard(item, role !== 'display' && day <= today)).join('')}</div></section>`] : [];
  });
  const history = data?.history || [];
  const calendarLabel = formatDay(day, { weekday: 'long', month: 'long', day: 'numeric' });
  return `<header class="greeting"><div><h1>Chore board</h1><p class="subtle">${h(calendarLabel)}</p></div>
      ${adult ? '<button class="primary" data-domain-open="chore">New chore</button>' : ''}</header>
    <div class="actions">
      <button class="secondary" data-chore-step="-1" aria-label="Previous chore day">‹</button>
      <button class="secondary" data-chore-step="0">Today</button>
      <button class="secondary" data-chore-step="1" aria-label="Next chore day">›</button>
      <label class="field">Chore date<input id="chore-date" type="date" value="${h(day)}"></label>
    </div>
    ${sections.join('') || '<p class="empty">No scheduled chores on this day.</p>'}
    ${legacy.length ? `<div class="section-head"><h2>To-dos</h2></div><div class="list">${legacy.map(renderTask).join('')}</div>` : ''}
    ${adult && data?.templates?.length ? `<details class="card domain-details"><summary>Manage chore schedules</summary>
      <div class="list">${data.templates.map(template => `<div class="row domain-row">
        <div><strong>${h(template.title)}</strong><div class="item-detail">${h(template.repeat)} · ${h(template.start_date)}</div></div>
        <button class="text-button" data-chore-edit="${h(template.id)}" aria-label="Edit chore ${h(template.title)}">Edit</button>
      </div>`).join('')}</div></details>` : ''}
    ${history.length ? `<details class="card domain-details" ${adult && history.some(entry => entry.status === 'pending') ? 'open' : ''}>
      <summary>Completion history</summary>
      <div class="list">${history.map(entry => `<div class="domain-row">
        <strong>${h(entry.title)}</strong>
        <p class="item-detail">${h(entry.member_name)} · ${h(entry.due_date)} · ${STATUS[entry.status]}</p>
        ${adult && entry.status === 'pending' ? `<div class="actions">
          <button class="primary" data-chore-review="${h(entry.id)}" data-approve="true" aria-label="Approve chore ${h(entry.title)}">Approve</button>
          <button class="secondary" data-chore-review="${h(entry.id)}" data-approve="false">Decline</button>
        </div>` : ''}
      </div>`).join('')}</div>
    </details>` : ''}`;
}

export function choreForm(template, members, today) {
  const assignments = template?.assignees.map(assignee => assignee.member_id) || [];
  return `<header class="greeting"><h1>${template ? 'Edit chore' : 'New chore'}</h1></header>
    <form id="chore-form" class="card form form-card">
      <label class="field">Chore name<input name="title" maxlength="120" value="${h(template?.title)}" required></label>
      <label class="field">Instructions<textarea name="details" maxlength="1000">${h(template?.details)}</textarea></label>
      <label class="field">First day<input type="date" name="start" value="${h(template?.start_date || today)}" required></label>
      <label class="field">Repeat<select name="repeat">
        ${[['once','Once'],['daily','Every day'],['weekly','Every week']].map(([id,label]) =>
          `<option value="${id}" ${template?.repeat === id ? 'selected' : ''}>${label}</option>`).join('')}
      </select></label>
      <label class="field">Routine<select name="routine">
        ${Object.entries(ROUTINES).map(([id,label]) => `<option value="${id}" ${(template?.routine || 'anytime') === id ? 'selected' : ''}>${label}</option>`).join('')}
      </select></label>
      <fieldset class="domain-fieldset"><legend>Assign to</legend>
        <p class="item-detail">Leave empty for one shared chore. Choose multiple members to give each person a chore.</p>
        ${members.filter(member => member.role !== 'display').map(member =>
          `<label class="calendar-checkbox"><input type="checkbox" name="assignees" value="${h(member.id)}"
            ${assignments.includes(member.id) ? 'checked' : ''}> ${h(member.display_name)}</label>`).join('')}
      </fieldset>
      <label class="field">Points<input type="number" name="points" min="0" max="10000" value="${template?.points || 0}" required></label>
      <label class="calendar-checkbox"><input type="checkbox" name="approvalRequired" ${template?.requires_approval ? 'checked' : ''}> Require adult approval</label>
      <div class="actions">
        <button class="primary">Save chore</button>
        <button class="secondary" data-nav="tasks" type="button">Cancel</button>
        ${template ? '<button class="secondary danger" data-chore-archive type="button">Archive schedule</button>' : ''}
      </div>
    </form>`;
}

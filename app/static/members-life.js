import { escapeHtml as h } from './html.js';

const currency = new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' });
const dollars = cents => currency.format(cents / 100);

export function habitsView(data) {
  return `<header class="greeting"><div><h1>Habits</h1><p class="subtle">${h(data?.date)}</p></div>
    <button class="primary" data-domain-open="habit">New habit</button></header>
    <div class="list">${data?.habits.length ? data.habits.map(habit => `<article class="card domain-row">
      <div class="actions"><strong class="item-title">${h(habit.title)}</strong><span class="badge">${habit.streak}-day streak</span></div>
      <p class="item-detail">${h([habit.display_name, habit.details].filter(Boolean).join(' · '))}</p>
      <div class="actions">
        <button class="primary" data-habit-check="${h(habit.id)}" ${habit.checked ? 'disabled' : ''}>${habit.checked ? 'Checked in today' : 'Check in today'}</button>
        <button class="text-button" data-habit-edit="${h(habit.id)}" aria-label="Edit habit ${h(habit.title)}">Edit</button>
      </div>
      ${habit.days.length ? `<details data-panel="habit-${h(habit.id)}"><summary>Recent check-ins</summary>
        <p class="item-detail">${h(habit.days.join(' · '))}</p></details>` : ''}
    </article>`).join('') : '<p class="empty">No habits to track yet.</p>'}</div>`;
}

export function habitForm(habit, members, adult, actor) {
  return `<header class="greeting"><h1>${habit ? 'Edit habit' : 'New habit'}</h1></header>
    <form id="habit-form" class="card form form-card">
      <label class="field">Habit name<input name="title" maxlength="120" value="${h(habit?.title)}" required></label>
      <label class="field">Notes<textarea name="details" maxlength="1000">${h(habit?.details)}</textarea></label>
      ${adult && !habit ? `<label class="field">Member<select name="memberId">${members.filter(member => member.role !== 'display').map(member =>
        `<option value="${h(member.id)}" ${member.id === actor ? 'selected' : ''}>${h(member.display_name)}</option>`).join('')}</select></label>` : ''}
      <div class="actions"><button class="primary">Save habit</button><button class="secondary" type="button" data-nav="habits">Cancel</button>
        ${habit ? '<button class="secondary danger" type="button" data-habit-archive>Archive</button>' : ''}</div>
    </form>`;
}

export function allowanceView(data, adult) {
  return `<header class="greeting"><h1>Allowance</h1></header>
    <div class="list">${data?.wallets.map(wallet => `<article class="card row dashboard-shopping">
      <strong>${h(wallet.display_name)}</strong><span>${dollars(wallet.balance)} available</span></article>`).join('') || ''}</div>
    ${adult && data?.wallets.length ? `<form class="card form form-card allowance-record" id="allowance-form">
      <h2>Record allowance</h2>
      <label class="field">Member<select name="memberId">${data.wallets.map(wallet => `<option value="${h(wallet.id)}">${h(wallet.display_name)}</option>`).join('')}</select></label>
      <label class="field">Type<select name="direction"><option value="credit">Credit</option><option value="paid">Payout</option></select></label>
      <label class="field">Amount in USD<input type="number" inputmode="decimal" name="amount" min="0.01" max="99999.99" step="0.01" required></label>
      <label class="field">Description<input name="note" maxlength="200" required></label>
      <button class="primary">Record entry</button>
    </form>` : ''}
    <div class="section-head"><h2>Recent entries</h2></div>
    <div class="list">${data?.entries.length ? data.entries.map(entry => `<article class="card row dashboard-shopping">
      <div><strong>${h(entry.note)}</strong><div class="item-detail">${h(entry.display_name)} · ${h(entry.created_at.slice(0, 10))}</div></div>
      <strong>${entry.amount_cents > 0 ? '+' : ''}${dollars(entry.amount_cents)}</strong>
    </article>`).join('') : '<p class="empty">No allowance entries.</p>'}</div>`;
}

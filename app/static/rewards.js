import { escapeHtml as h } from './html.js';

const STATUS = { pending: 'Waiting for approval', approved: 'Approved', declined: 'Declined' };

export function rewardsView(data, role, actor) {
  const adult = ['owner', 'admin', 'adult'].includes(role);
  const store = data ? [...data.rewards, ...(adult ? data.legacy : [])] : [];
  return `<header class="greeting"><div><h1>Rewards</h1><p class="subtle">Your balance · ${data?.balance || 0} points</p></div>
    ${adult ? '<button class="primary" data-domain-open="reward">New reward</button>' : ''}
  </header>
  <div class="list">${store.length ? store.map(item => {
    const pending = data.requests.some(entry => entry.reward_id === item.id && entry.member_id === actor && entry.status === 'pending');
    return `<article class="card domain-row"><div class="item-title">${h(item.title)}</div>
      ${item.details ? `<p class="item-detail">${h(item.details)}</p>` : ''}
      <p class="item-detail">${item.points ? `${item.points} points` : 'Set a point price to add this reward to the store.'}</p>
      <div class="actions">
        ${item.points && role !== 'display' ? `<button class="primary" data-reward-request="${h(item.id)}" aria-label="Request reward ${h(item.title)}"
          ${pending || data.balance < item.points ? 'disabled' : ''}>${pending ? 'Requested' : data.balance < item.points ? 'Need more points' : 'Request reward'}</button>` : ''}
        ${adult ? `<button class="text-button" data-reward-edit="${h(item.id)}" aria-label="Edit reward ${h(item.title)}">Edit</button>` : ''}
      </div></article>`;
  }).join('') : '<p class="empty">No rewards in the store yet.</p>'}</div>
  ${data?.requests.length ? `<div class="section-head"><h2>Redemptions</h2></div>
    <div class="list">${data.requests.map(entry => `<article class="card domain-row">
      <strong>${h(entry.title)}</strong><p class="item-detail">${h(entry.member_name)} · ${entry.cost} points · ${STATUS[entry.status]}</p>
      ${adult && entry.status === 'pending' ? `<div class="actions">
        <button class="primary" data-reward-review="${h(entry.id)}" data-approve="true" aria-label="Approve reward ${h(entry.title)}">Approve</button>
        <button class="secondary" data-reward-review="${h(entry.id)}" data-approve="false">Decline</button>
      </div>` : ''}</article>`).join('')}</div>` : ''}`;
}

export function rewardForm(reward) {
  return `<header class="greeting"><h1>${reward ? 'Edit reward' : 'New reward'}</h1></header>
    <form id="reward-form" class="card form form-card">
      <label class="field">Reward name<input maxlength="120" name="title" value="${h(reward?.title)}" required></label>
      <label class="field">Description<textarea maxlength="1000" name="details">${h(reward?.details)}</textarea></label>
      <label class="field">Point price<input type="number" name="points" min="1" max="10000" value="${reward?.points || 1}" required></label>
      <div class="actions">
        <button class="primary">Save reward</button>
        <button class="secondary" data-nav="rewards" type="button">Cancel</button>
        ${reward ? '<button class="secondary danger" type="button" data-reward-archive>Archive reward</button>' : ''}
      </div>
    </form>`;
}

import { escapeHtml as h } from './html.js';

const LOCATIONS = { pantry: 'Pantry', refrigerator: 'Refrigerator', freezer: 'Freezer' };
const choices = (locations, selected) => Object.entries(locations).map(([id, label]) =>
  `<option value="${id}" ${id === selected ? 'selected' : ''}>${label}</option>`).join('');

export function inventoryView(data, current, adult) {
  return `<header class="greeting"><h1>Food inventory</h1>
    ${adult ? '<button class="primary" data-domain-open="inventory">New stock item</button>' : ''}
  </header>
  <label class="field inventory-filter">Location<select id="inventory-location">
    ${choices({ '': 'All locations', ...LOCATIONS }, current)}
  </select></label>
  <div class="list">${data?.items.length ? data.items.map(item => `<article class="card domain-row">
    <div class="row"><strong class="item-title">${h(item.title)}</strong>
      ${item.low ? '<span class="badge">Low stock</span>' : ''}
      ${item.expired ? '<span class="badge">Past expiry</span>' : ''}</div>
    <p class="item-detail">${h([LOCATIONS[item.location], item.quantity != null ? `${item.quantity} ${item.unit}`.trim() : 'Stock details needed',
      item.expires_on ? `Expires ${item.expires_on}` : '', item.details].filter(Boolean).join(' · '))}</p>
    ${adult ? `<div class="actions"><button type="button" class="text-button" data-inventory-edit="${h(item.id)}" aria-label="Edit stock item ${h(item.title)}">Edit</button></div>` : ''}
    ${adult && item.quantity != null ? `<details data-panel="stock-${h(item.id)}"><summary>Adjust stock</summary>
      <form class="actions inventory-stock-form" data-stock-item="${h(item.id)}">
        <label class="field">Action<select name="direction"><option value="use">Use</option><option value="restock">Restock</option></select></label>
        <label class="field">Amount<input name="amount" type="number" inputmode="decimal" min="0.0001" max="999999.9999" step="0.0001" required></label>
        <button class="secondary">Record change</button>
      </form></details>` : ''}
  </article>`).join('') : '<p class="empty">No items in this location.</p>'}</div>
  ${data?.history.length ? `<details class="card domain-details" data-panel="inventory-history"><summary>Stock history</summary>
    <div class="list">${data.history.map(item => `<div>${h(item.title)} · ${item.direction === 'use' ? 'Used' : 'Restocked'}
      ${h(item.amount)} ${h(item.unit)} <span class="item-detail">${h(item.created_at.slice(0, 10))}</span></div>`).join('')}</div></details>` : ''}`;
}

export function inventoryForm(item, current) {
  return `<header class="greeting"><h1>${item ? 'Edit stock item' : 'New stock item'}</h1></header>
    <form class="card form form-card" id="inventory-form">
      <label class="field">Item name<input name="title" value="${h(item?.title)}" maxlength="120" required></label>
      <label class="field">Location<select name="location">${choices(LOCATIONS, item?.location || current)}</select></label>
      <label class="field">Quantity<input name="quantity" type="number" inputmode="decimal" min="0" max="999999.9999"
        step="0.0001" value="${h(item?.quantity ?? '1')}" required></label>
      <label class="field">Unit<input name="unit" maxlength="40" value="${h(item?.unit)}"></label>
      <label class="field">Low-stock threshold<input name="threshold" type="number" inputmode="decimal" min="0"
        max="999999.9999" step="0.0001" value="${h(item?.threshold ?? '0')}" required></label>
      <label class="field">Expires on<input name="expiresOn" type="date" value="${h(item?.expires_on)}"></label>
      <label class="field">Notes<textarea name="details" maxlength="1000">${h(item?.details)}</textarea></label>
      <div class="actions">
        <button class="primary">Save stock item</button><button type="button" class="secondary" data-nav="inventory">Cancel</button>
        ${item ? '<button type="button" class="secondary danger" data-inventory-archive>Archive</button>' : ''}
      </div>
    </form>`;
}

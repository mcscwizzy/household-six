import { escapeHtml as h } from './html.js';

export function shoppingView(data, { canEdit, canCreateList, mode, editing }) {
  if (!data) return '<h1>Shopping lists</h1><p>Connect to load your shopping lists.</p>';
  const options = data.lists.map(list => `<option value="${h(list.id)}" ${list.id === data.list.id ? 'selected' : ''}>${h(list.name)}</option>`).join('');
  const open = data.items.filter(item => !item.completed);
  const done = data.items.filter(item => item.completed);
  const groups = new Map();
  for (const item of open) {
    const category = item.category || 'Uncategorized';
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(item);
  }
  const renderGroup = (name, items) => `<section class="shopping-group"><h2>${h(name)}</h2>
    <ul class="shopping-items">${items.map(item => shoppingItem(item, canEdit, mode)).join('')}</ul></section>`;
  return `<header class="greeting"><h1>Shopping lists</h1></header>
    <div class="shopping-toolbar">
      <label class="field">Shared list<select id="shopping-list">${options}</select></label>
      <button class="secondary" data-shopping-mode aria-pressed="${mode}">${mode ? 'Exit shopping mode' : 'Shopping mode'}</button>
    </div>
    ${canCreateList && !mode ? `<details class="card shopping-create-list"><summary>New list</summary>
      <form id="shopping-list-form" class="form">
        <label class="field">List name<input name="name" maxlength="60" required></label>
        <button class="primary">Create list</button>
      </form>
    </details>` : ''}
    ${canEdit && !mode ? itemForm(editing) : ''}
    <p class="subtle">${open.length} to get · ${done.length} completed</p>
    ${open.length ? [...groups].map(([name, group]) => renderGroup(name, group)).join('') : '<p class="empty">Nothing to get on this list.</p>'}
    ${done.length && !mode ? renderGroup('Completed', done) : ''}`;
}

function shoppingItem(item, canEdit, mode) {
  const details = [item.quantity, !mode && item.details].filter(Boolean).map(h).join(' · ');
  return `<li class="card row item-card ${mode ? 'shopping-mode-item' : ''}">
    ${canEdit && !item.completed
      ? `<button class="check" data-complete="${h(item.id)}" aria-label="Complete ${h(item.title)}"></button>`
      : item.completed ? '<span class="badge" aria-label="Completed">✓</span>' : ''}
    <div class="item-main"><strong class="item-title">${h(item.title)}</strong>
      ${details ? `<div class="item-detail">${details}</div>` : ''}</div>
    ${canEdit && !mode ? `<button class="text-button" data-shopping-edit="${h(item.id)}" aria-label="Edit ${h(item.title)}">Edit</button>` : ''}
  </li>`;
}

function itemForm(item) {
  return `<form id="shopping-item-form" class="card form">
    <h2>${item ? 'Edit item' : 'Add item'}</h2>
    <div class="shopping-fields">
      <label class="field">Item name<input name="title" value="${h(item?.title)}" maxlength="120" required></label>
      <label class="field">Quantity<input name="quantity" value="${h(item?.quantity)}" maxlength="40" placeholder="2 bags"></label>
      <label class="field">Category<input name="category" value="${h(item?.category)}" maxlength="60" placeholder="Produce"></label>
    </div>
    <label class="field">Notes<input name="details" value="${h(item?.details)}" maxlength="1000"></label>
    <div class="actions">
      <button class="primary">${item ? 'Save item' : 'Add to list'}</button>
      ${item ? '<button class="secondary" data-shopping-cancel type="button">Cancel</button><button class="secondary danger" data-shopping-delete type="button">Delete item</button>' : ''}
    </div>
  </form>`;
}

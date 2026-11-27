import { escapeHtml as h } from './html.js';

const TYPES = [['grocery','Grocery list'], ['calendar','Calendar event'], ['chore','Chore'],
  ['question','Household question'], ['recipe','Recipe extraction'], ['document','Document or image extraction']];
const STATUS = { queued: 'Queued', running: 'Processing', proposal: 'Review before saving', result: 'Result',
  applied: 'Saved', dismissed: 'Dismissed', failed: 'Could not process' };

function preview(result) {
  if (!result) return '';
  if (result.message) return `<p>${h(result.message)}</p>`;
  if (result.lines) return result.lines.length ? `<ul>${result.lines.map(line => `<li>${h(line)}</li>`).join('')}</ul>` : '<p>No matching entries.</p>';
  if (result.extracted_text !== undefined) {
    return `<h3>${h(result.title || 'Extracted text')}</h3><p>${h(result.summary)}</p><p class="six-text">${h(result.extracted_text)}</p>`;
  }
  const fields = result.data;
  if (!fields) return '';
  if (result.kind === 'grocery') return `<ul>${fields.items.map(item => `<li>${h(item.title)} ${h(item.quantity)}</li>`).join('')}</ul>`;
  const details = [fields.start, fields.end, fields.repeat, fields.routine,
    fields.servings ? `${fields.servings} servings` : ''].filter(Boolean);
  return `<h3>${h(fields.title)}</h3><p>${h(details.join(' · '))}</p>
    ${fields.ingredients ? `<ul>${fields.ingredients.map(item => `<li>${h(item.quantity)} ${h(item.unit)} ${h(item.name)}</li>`).join('')}</ul>` : ''}
    ${fields.instructions ? `<p class="six-text">${h(fields.instructions)}</p>` : ''}`;
}

export function sixView(data) {
  return `<header class="greeting"><h1>Six</h1></header>
    ${data?.modelEnabled ? `<form class="card form form-card" id="six-form">
      <label class="field">Action<select name="kind">${TYPES.map(([id,label]) => `<option value="${id}">${label}</option>`).join('')}</select></label>
      <label class="field">Request or source text<textarea name="text" maxlength="6000" placeholder="Add 2 bags of oats to groceries"></textarea></label>
      <label class="field" id="six-attachment-field" hidden>Optional file<input type="file" name="attachment" accept=".txt,.pdf,image/png,image/jpeg"></label>
      <button class="primary">Send to Six</button>
    </form>` : '<p class="subtle">Local model inference is disabled.</p>'}
    <div class="section-head"><h2>Requests</h2><button class="text-button" data-six-refresh>Refresh</button></div>
    <div class="list">${data?.jobs.length ? data.jobs.map(job => `<article class="card domain-row">
      <strong>${h(TYPES.find(([id]) => id === job.kind)?.[1] || 'Local integration')}</strong>
      <p class="item-detail">${STATUS[job.state]}</p>
      ${preview(job.result)}
      ${job.state === 'proposal' ? `<div class="actions">
        <button type="button" class="primary" data-six-decision="${h(job.id)}" data-six-confirm="true">Apply proposal</button>
        <button type="button" class="secondary" data-six-decision="${h(job.id)}" data-six-confirm="false">Dismiss</button>
      </div>` : ''}
    </article>`).join('') : '<p class="empty">No recent requests.</p>'}</div>`;
}

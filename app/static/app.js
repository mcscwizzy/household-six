import { dashboardView } from './dashboard.js';
import { calendarForm, calendarView, moveCalendar, rangeFor } from './calendar.js';
import { householdDate, shiftDay } from './dates.js';
import { shoppingView } from './shopping.js';
import { escapeHtml as esc } from './html.js';
import { clearLegacyCaches, clearQueued, queuedFor, removeQueued, storeQueued } from './offline.js';
const $=s=>document.querySelector(s);const app=$('#app');
const modules={today:['Today','☀️'],calendar:['Calendar','▦'],tasks:['Tasks','✓'],meals:['Meals','♨'],more:['More','⌘'],shopping:['Shopping lists','🛒'],recipes:['Recipes','🍲'],inventory:['Pantry & freezer','🥕'],rewards:['Rewards','⭐'],announcements:['Announcements','📌']};
let me=null,csrf='',screen='today',members=[],items=[],message='',error='',offline=false,authState='signed-out',live=null,quickOpen=false;
let shoppingData = null;
let shoppingList = 'default';
let shoppingMode = false;
let editingShoppingItem = null;
let loadSequence = 0;
let calendarData = null;
let dashboardData = null;
let calendarState = { anchor: null, view: 'month', member: '' };
let calendarDraft = null;
let calendarOccurrence = null;
let calendarAllDay = false;


function resetShopping() {
  calendarData = null;
  dashboardData = null;
  calendarState = { anchor: null, view: 'month', member: '' };
  calendarDraft = null;
  calendarOccurrence = null;
  shoppingData = null;
  shoppingList = 'default';
  shoppingMode = false;
  editingShoppingItem = null;
  loadSequence++;
}

async function expireLocalSession(){const expiredId=me?.id;if(expiredId)try{await clearQueued(expiredId)}catch{}clearLegacyCaches();resetShopping();me=null;csrf='';members=[];items=[];offline=false;authState='signed-out';if(live){live.close();live=null}renderAuth(false)}
clearLegacyCaches();
function formHasDraft(){
  if (screen === 'calendar-form' || document.querySelector('#calendar-import input')?.files?.length) return true;
  const shoppingForm = document.activeElement?.closest('#shopping-item-form, #shopping-list-form');
  if (shoppingForm || editingShoppingItem) return screen === 'shopping';
if(!screen.startsWith('new:'))return false;const form=$('#item-form');return !!form&&(form.contains(document.activeElement)||Array.from(new FormData(form).values()).some(Boolean))}
function setNotice(text,isError=false){message=isError?'':text;error=isError?text:'';render()}
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(options.method&&options.method!=='GET'&&csrf)headers['X-CSRF-Token']=csrf;return fetch(path,{...options,headers,credentials:'same-origin'})}
function navButton(id,side=false){const [name,icon]=modules[id];return `<button class="${side?'side-button':'nav-item'} ${screen===id?'active':''}" data-nav="${id}">${side?`<span>${icon}</span><span>${name}</span>`:`<span class="nav-icon">${icon}</span><span>${name==='Shopping lists'?'Lists':name}</span>`}</button>`}
function shell(content){return `<div class="shell"><aside class="side"><div class="side-brand"><img src="/logo.svg" alt=""><span>Household Six</span></div>${['today','calendar','tasks','meals','more'].map(x=>navButton(x,true)).join('')}<div class="side-spacer"></div><button class="side-button" data-action="theme">◐ <span>Appearance</span></button></aside><header class="topbar"><div class="brand"><img src="/logo.svg" alt=""><span>Household Six</span></div><div class="top-actions"><span class="connection ${offline?'offline':''}">${authState==='offline-authorized'?'Offline authorized · changes pending':'● Local & private'}</span><button class="theme" data-action="theme" aria-label="Toggle appearance">◐</button></div></header><main class="main">${message?`<div class="notice">${esc(message)}</div>`:''}${error?`<div class="notice error">${esc(error)}</div>`:''}${content}<p class="footer-note">Your household. Your hardware. Your data.</p></main><nav class="bottom-nav" aria-label="Main navigation">${['today','calendar','tasks','meals','more'].map(x=>navButton(x)).join('')}</nav>${!['shopping','calendar','calendar-form'].includes(screen)&&canCreateKind(screen==='tasks'?'task':screen==='events'?'event':screen)?'<button class="quick" data-action="add" aria-label="Add item">+</button>':''}${quickOpen?quickMenu():''}</div>`}
function memberChips(balances){return `<div class="member-row">${balances.map(m=>`<div class="member"><span class="avatar color-${avatarColor(m.color)}">${esc(m.display_name.slice(0,1).toUpperCase())}</span>${esc(m.display_name)}${` · ${m.points} pts`}</div>`).join('')}</div>`}
function avatarColor(color){return ({'#233C32':'forest','#78937D':'sage','#C69A5D':'gold','#54768C':'blue','#9B6B72':'rose','#7B6C9B':'violet'})[color]||'sage'}
function canCreateKind(kind){if(!me||me.role==='display')return false;if(['owner','admin','adult'].includes(me.role))return true;return me.role==='child'&&['task','shopping'].includes(kind)}
function quickMenu(){const choices=[['task','Task'],['event','Calendar event'],['shopping','Shopping item'],['meal','Meal'],['inventory','Inventory item'],['recipe','Recipe'],['reward','Reward'],['announcement','Announcement']].filter(([kind])=>canCreateKind(kind));return `<div class="quick-menu card" role="group" aria-label="Quick add">${choices.map(([kind,label])=>`<button class="quick-choice" data-new-kind="${kind}">${label}</button>`).join('')}</div>`}
function itemCard(item){const who=item.assigned_name||members.find(m=>m.id===item.assigned_to)?.display_name;const completable=['task','shopping'].includes(item.kind);const label={event:'Scheduled',meal:'Planned',inventory:'In stock',recipe:'Saved',reward:'Available',announcement:'Posted'}[item.kind]||'Saved';const control=me.role==='display'?`<span class="badge">${item.completed?'Done':'Read only'}</span>`:completable?`<button class="check ${item.completed?'done':''}" data-complete="${esc(item.id)}" aria-label="${item.completed?'Completed':'Complete'} ${esc(item.title)}">${item.completed?'✓':''}</button>`:`<span class="badge">${item.completed?'Done':label}</span>`;return `<article class="card row item-card ${item.completed?'completed':''}">${control}<div class="item-main"><div class="item-title">${esc(item.title)}</div><div class="item-detail">${esc(item.details||item.due_at||'')}${who?' · '+esc(who):''}</div></div>${item.value?`<span class="badge">⭐ ${item.value}</span>`:''}</article>`}
function listContent(title,kind,description=''){const rows=items.filter(i=>i.kind===kind);return `<div class="greeting"><div><div class="eyebrow">${esc(me.household)}</div><h1>${esc(title)}</h1><div class="subtle">${esc(description)}</div></div></div><div class="section-head"><h2>${rows.length?`${rows.length} items`:'Ready when you are'}</h2>${canCreateKind(kind)?'<button class="text-button" data-action="add">＋ Add</button>':''}</div>${rows.length?`<div class="list">${rows.map(itemCard).join('')}</div>`:`<div class="empty"><strong>No ${esc(title.toLowerCase())} yet</strong>${me.role==='display'?'No items have been added yet.':canCreateKind(kind)?'Add your first item to get started.':'Ask an adult to add an item.'}</div>`}`}
function moreView(){const tiles=['shopping','recipes','inventory','rewards','announcements'];return `<div class="greeting"><div><div class="eyebrow">Your family toolkit</div><h1>More</h1><div class="subtle">Everything the household shares.</div></div></div><div class="more-grid">${tiles.map(id=>`<button class="card more-tile" data-nav="${id}"><span class="tile-icon">${modules[id][1]}</span><strong>${modules[id][0]}</strong><span class="item-detail">Open shared ${modules[id][0].toLowerCase()}</span></button>`).join('')}<button class="card more-tile" data-nav="members"><span class="tile-icon">👨‍👩‍👧</span><strong>Members</strong><span class="item-detail">Household profiles</span></button><button class="card more-tile" data-nav="settings"><span class="tile-icon">⚙️</span><strong>Settings</strong><span class="item-detail">Account and privacy</span></button></div>`}
function formView(kind){const label={task:'Task',event:'Calendar event',shopping:'Shopping item',meal:'Meal',inventory:'Inventory item',recipe:'Recipe',reward:'Reward',announcement:'Announcement'}[kind]||'Item';return `<div class="greeting"><div><div class="eyebrow">${esc(me.household)}</div><h1>Add ${label.toLowerCase()}</h1><div class="subtle">Your change is saved to your household server.</div></div></div><form class="card form-card form" id="item-form"><label class="field">Title<input name="title" maxlength="120" required autofocus placeholder="${kind==='shopping'?'e.g. Milk':'What would you like to add?'}"></label><label class="field">Notes<textarea name="details" maxlength="1000" placeholder="Add a helpful note (optional)"></textarea></label>${['task','event','meal','inventory'].includes(kind)?`<label class="field">${kind==='event'?'Date and time':'Date'}<input name="dueAt" type="${kind==='event'?'datetime-local':'date'}"></label>`:''}${kind==='task'&&me.role!=='child'?`<label class="field">Assign to<select name="assignedTo"><option value="">Anyone</option>${members.map(m=>`<option value="${esc(m.id)}">${esc(m.display_name)}</option>`).join('')}</select></label><label class="field">Points for completion<input type="number" name="points" min="0" max="10000" value="0"></label>`:''}<div class="actions"><button class="primary" type="submit">Save ${label.toLowerCase()}</button><button class="secondary" type="button" data-nav="${kind==='event'?'calendar':kind==='task'?'tasks':'more'}">Cancel</button></div></form>`}
function memberView(){return `<div class="greeting"><div><div class="eyebrow">Household profiles</div><h1>Members</h1><div class="subtle">Everyone who shares your household.</div></div></div><div class="list">${members.map(m=>`<div class="card row item-card"><span class="avatar color-${avatarColor(m.color)}">${esc(m.display_name[0])}</span><div class="item-main"><div class="item-title">${esc(m.display_name)}</div><div class="item-detail">${esc(m.role)}</div></div></div>`).join('')}</div>${me.role==='owner'||me.role==='admin'?`<div class="section-head"><h2>Add a member</h2></div><form id="member-form" class="card form"><label class="field">Name<input name="displayName" required></label><label class="field">Username<input name="username" minlength="3" required></label><label class="field">Role<select name="role">${(me.role==='owner'?['admin','adult','child','display']:['adult','child','display']).map(role=>`<option value="${role}">${role==='admin'?'Administrator':role==='child'?'Child profile':role==='display'?'Read-only display':'Adult'}</option>`).join('')}</select></label><label class="field">Member color<select name="color">
  <option value="#78937D">Sage</option><option value="#233C32">Forest</option>
  <option value="#C69A5D">Gold</option><option value="#54768C">Blue</option>
  <option value="#9B6B72">Rose</option><option value="#7B6C9B">Violet</option></select></label>
  <label class="field">Password (required to sign in; 12+ characters)<input name="password" type="password" minlength="12"></label><button class="primary">Add household member</button></form>`:''}`}
function settingsView(){return `<div class="greeting"><div><div class="eyebrow">Account</div><h1>Settings</h1><div class="subtle">Signed in as ${esc(me.displayName)} (${esc(me.role)}).</div></div></div><div class="card form"><div><strong>${esc(me.household)}</strong><div class="item-detail">Timezone: ${esc(me.timezone)}</div></div><label class="field">Appearance<select id="theme-select"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><form id="password-form" class="form"><div class="section-head"><h2>Change password</h2></div><label class="field">Current password<input type="password" name="currentPassword" required autocomplete="current-password"></label><label class="field">New password<input type="password" name="newPassword" minlength="12" required autocomplete="new-password"></label><button class="primary">Update password</button></form><button class="secondary" data-action="logout">Sign out</button><div class="item-detail">Your local household server holds your account and family data. No analytics or cloud account is used.</div></div>`}
function render(){if(!me){renderAuth();return}let content=screen==='today'?dashboardView(dashboardData, me.household, canCreateKind('task'), itemCard, memberChips):screen==='calendar'?calendarView(calendarData, calendarState, members, canCreateKind('event'))
  :screen==='calendar-form'?calendarForm(calendarDraft, members, calendarState.anchor, calendarOccurrence, calendarAllDay):screen==='tasks'?listContent('Tasks','task','Chores and the things to do.'):screen==='meals'?listContent('Meals','meal','Plan what your family will enjoy.'):screen==='more'?moreView():screen==='members'?memberView():screen==='settings'?settingsView():screen==='shopping'?shoppingView(shoppingData, {
  canEdit: canCreateKind('shopping'), canCreateList: ['owner', 'admin', 'adult'].includes(me.role),
  mode: shoppingMode, editing: editingShoppingItem,
}):screen==='recipes'?listContent('Recipes','recipe','Your household cookbook.'):screen==='inventory'?listContent('Pantry & freezer','inventory','Know what you have at home.'):screen==='rewards'?listContent('Rewards','reward','Family rewards and favorites.'):screen==='announcements'?listContent('Announcements','announcement','Notes for everyone at home.'):screen.startsWith('new:')?formView(screen.slice(4)):'';app.innerHTML=shell(content);const themeSelect=$('#theme-select');if(themeSelect)themeSelect.value=localStorage.getItem('hs-theme')||'system';}
function renderAuth(setup=false){const title=setup?'Set up your household':'Welcome back';app.innerHTML=`<main class="auth"><section class="card auth-card"><div class="auth-brand"><img src="/logo.svg" alt=""><div><h1>Household Six</h1><p>Your household. Your hardware. Your data.</p></div></div>${error?`<div class="notice error">${esc(error)}</div>`:''}<form class="form" id="auth-form">${setup?`<label class="field">Household name<input name="household" required maxlength="70" placeholder="The Johnson Family"></label><label class="field">Your name<input name="displayName" required maxlength="70"></label>`:''}<label class="field">Username<input name="username" required minlength="3" autocomplete="username"></label><label class="field">Password<input name="password" type="password" required minlength="${setup?12:1}" autocomplete="${setup?'new-password':'current-password'}">${setup?'<span class="item-detail">Use at least 12 characters. This account is the local owner.</span>':''}</label><button class="primary">${setup?'Create household':'Sign in'}</button></form><p class="footer-note">Stored on your household server. No account with an outside service is needed.</p></section></main>`;$('#auth-form').addEventListener('submit',authSubmit)}
async function authSubmit(event){event.preventDefault();const f=new FormData(event.currentTarget),setup=!!f.get('household');try{const res=await fetch(setup?'/api/setup':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(Object.fromEntries(f))});const data=await res.json();if(!res.ok)throw Error(data.error);me=data.user;csrf=data.csrf;authState='authenticated';await loadData();startLive();}catch(e){error=e.message||'Could not reach your household server.';renderAuth(setup)}}
async function loadData() {
  if (!me) return;
  const memberId = me.id;
  const view = screen;
  const sequence = ++loadSequence;
  const current = () => sequence === loadSequence && me?.id === memberId && screen === view;
  const kinds = [{ calendar: 'event', tasks: 'task', meals: 'meal', recipes: 'recipe',
        inventory: 'inventory', rewards: 'reward', announcements: 'announcement' }[view] || 'task'];
  if (!calendarState.anchor) calendarState.anchor = householdDate(me.timezone);
  const range = rangeFor(calendarState);
  const calendarQuery = new URLSearchParams({ from: range.start, to: range.end, member: calendarState.member });
  const paths = ['/api/members', '/api/summary', ...(view === 'today' ? ['/api/dashboard'] : view === 'calendar'
    ? [`/api/calendar?${calendarQuery}`] : view === 'shopping'
    ? [`/api/shopping?list=${encodeURIComponent(shoppingList)}`]
    : kinds.map(kind => `/api/items?kind=${kind}`))];
  try {
    const responses = await Promise.all(paths.map(path => api(path)));
    if (!current()) return;
    if (responses.some(response => response.status === 401)) {
      await expireLocalSession();
      return;
    }
    if (responses.some(response => !response.ok)) throw Error('Household data could not be refreshed.');
    const [directory, summary, ...records] = await Promise.all(responses.map(response => response.json()));
    if (!current()) return;
    members = directory.members.map(member => ({
      ...member, points: summary.members.find(entry => entry.id === member.id)?.points || 0,
    }));
    if (view === 'today') {
      dashboardData = records[0];
      items = [...dashboardData.chores, ...dashboardData.overdue, ...dashboardData.unscheduled];
    } else if (view === 'calendar') {
      calendarData = records[0];
      items = [];
    } else if (view === 'shopping') {
      shoppingData = records[0];
      items = shoppingData.items;
    } else {
      items = records.flatMap(record => record.items);
    }
    offline = false;
    authState = 'authenticated';
    if (!formHasDraft()) render();
    void flushQueue();
  } catch (err) {
    if (!current()) return;
    offline = err instanceof TypeError || !navigator.onLine;
    if (offline) authState = 'offline-authorized';
    else error = err.message;
    if (!formHasDraft()) render();
  }
}

function openCalendarForm(event = null, occurrence = null) {
  calendarDraft = event;
  calendarOccurrence = occurrence;
  calendarAllDay = event?.allDay || false;
  if (!calendarState.anchor) calendarState.anchor = householdDate(me.timezone);
  screen = 'calendar-form';
  error = '';
  message = '';
  render();
}

function calendarFields(form) {
  const fields = Object.fromEntries(new FormData(form));
  const rule = fields.repeat === 'imported' ? calendarDraft?.rule : undefined;
  return {
    ...fields, allDay: calendarAllDay, rule,
    repeat: rule ? '' : fields.repeat,
    exceptions: fields.exceptions.split(/[,\s]+/).filter(Boolean),
    expectedVersion: calendarDraft?.version,
  };
}

async function saveCalendar(path, method, fields) {
  const memberId = me?.id;
  const view = screen;
  try {
    const response = await api(path, {
      method, body: JSON.stringify({ ...fields, csrf, mutationId: crypto.randomUUID() }),
    });
    if (me?.id !== memberId || screen !== view) return;
    if (response.status === 401) return expireLocalSession();
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) throw Error(data.error || 'The event could not be saved.');
    if (data?.start && method === 'POST') calendarState.anchor = data.start.slice(0, 10);
    if (path.endsWith('/import')) document.querySelector('#calendar-import').reset();
    message = path.endsWith('/import') ? `Imported ${data.created} events.` : 'Calendar updated.';
    error = '';
    calendarDraft = null;
    screen = 'calendar';
    await loadData();
  } catch (err) {
    if (me?.id !== memberId || screen !== view) return;
    showFormError(err instanceof TypeError ? 'Reconnect to change the calendar.' : err.message);
  }
}

function showFormError(text) {
  error = text;
  const main = document.querySelector('.main');
  if (!main) return;
  let notice = main.querySelector('.notice.error');
  if (!notice) {
    notice = document.createElement('div');
    notice.className = 'notice error';
    notice.setAttribute('role', 'alert');
    main.prepend(notice);
  }
  notice.textContent = text;
}

app.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button || !me) return;
  const action = button.dataset;
  if (action.dashboardList) {
    shoppingList = action.dashboardList;
    screen = 'shopping';
    void loadData();
    return;
  }
  if ('calendarNew' in action) return openCalendarForm();
  if ('calendarEdit' in action) {
    const selected = [...(calendarData?.events || []), ...(calendarData?.unscheduled || [])]
      .find(entry => entry.id === action.calendarEdit);
    if (selected) openCalendarForm(selected, action.calendarOccurrence);
    return;
  }
  if ('calendarDelete' in action) {
    if (calendarDraft?.id && window.confirm('Delete this event and its recurring dates?')) {
      void saveCalendar(`/api/calendar/${encodeURIComponent(calendarDraft.id)}`, 'DELETE', { expectedVersion: calendarDraft.version });
    }
    return;
  }
  if ('calendarSkip' in action) {
    const { id, title, details, start, end, allDay, assignedTo, rule, version, exceptions } = calendarDraft;
    void saveCalendar(`/api/calendar/${encodeURIComponent(id)}`, 'PUT', {
      title, details, start, end, allDay, assignedTo: assignedTo || '', rule, expectedVersion: version,
      exceptions: [...new Set([...exceptions, action.calendarSkip])],
    });
    return;
  }
  if ('calendarCancel' in action) {
    screen = 'calendar';
    calendarDraft = null;
  } else if (action.calendarView) calendarState.view = action.calendarView;
  else if (action.calendarDay) {
    calendarState.anchor = action.calendarDay;
    calendarState.view = 'day';
  } else if (action.calendarStep) calendarState.anchor = moveCalendar(calendarState, Number(action.calendarStep));
  else if ('calendarToday' in action) calendarState.anchor = householdDate(me.timezone);
  else return;
  error = '';
  void loadData();
});

app.addEventListener('change', event => {
  if (event.target.id === 'calendar-member') {
    calendarState.member = event.target.value;
    void loadData();
  } else if (event.target.name === 'allDay' && event.target.form?.id === 'calendar-event-form') {
    const fields = calendarFields(event.target.form);
    calendarAllDay = event.target.checked;
    if (calendarAllDay && fields.start && fields.start.slice(0, 10) === fields.end.slice(0, 10)) {
      fields.end = shiftDay(fields.start.slice(0, 10), 1);
    }
    calendarDraft = { ...calendarDraft, ...fields, rule: fields.rule || (fields.repeat ? `FREQ=${fields.repeat.toUpperCase()}` : null) };
    render();
  }
});

app.addEventListener('submit', async event => {
  const form = event.target;
  if (form.id === 'calendar-event-form') {
    event.preventDefault();
    const path = calendarDraft?.id ? `/api/calendar/${encodeURIComponent(calendarDraft.id)}` : '/api/calendar';
    void saveCalendar(path, calendarDraft?.id ? 'PUT' : 'POST', calendarFields(form));
  }
  if (form.id === 'calendar-import') {
    event.preventDefault();
    const file = form.elements.ics.files[0];
    if (file.size > 128000) {
      showFormError('Choose an iCalendar file up to 128 KB.');
      return;
    }
    void saveCalendar('/api/calendar/import', 'POST', { ics: await file.text() });
  }
});

async function saveShopping(path, method, fields) {
  const memberId = me?.id;
  try {
    const response = await api(path, {
      method, body: JSON.stringify({ ...fields, csrf, mutationId: crypto.randomUUID() }),
    });
    if (me?.id !== memberId || screen !== 'shopping') return;
    if (response.status === 401) return expireLocalSession();
    const result = response.status === 204 ? null : await response.json();
    if (!response.ok) throw Error(result.error || 'The shopping change could not be saved.');
    editingShoppingItem = null;
    if (path.endsWith('/lists')) shoppingList = result.id;
    message = 'Shopping list updated.';
    error = '';
    render(); // release form focus before the refreshed data arrives
    await loadData();
  } catch (err) {
    if (me?.id !== memberId || screen !== 'shopping') return;
    showFormError(err instanceof TypeError ? 'Reconnect to change this shopping list.' : err.message);
  }
}

app.addEventListener('change', async event => {
  if (event.target.id !== 'shopping-list') return;
  shoppingList = event.target.value;
  editingShoppingItem = null;
  await loadData();
});
app.addEventListener('click', event => {
  const control = event.target.closest('[data-shopping-mode], [data-shopping-edit], [data-shopping-cancel], [data-shopping-delete]');
  if (!control) return;
  if ('shoppingDelete' in control.dataset) {
    const item = editingShoppingItem;
    if (item && window.confirm(`Delete ${item.title} from this shopping list?`)) {
      void saveShopping(`/api/shopping/items/${encodeURIComponent(item.id)}`, 'DELETE', { expectedVersion: item.version });
    }
    return;
  }
  if ('shoppingMode' in control.dataset) shoppingMode = !shoppingMode;
  editingShoppingItem = items.find(item => item.id === control.dataset.shoppingEdit) || null;
  render();
  if (editingShoppingItem) document.querySelector('#shopping-item-form input')?.focus();
});
app.addEventListener('submit', event => {
  const form = event.target;
  if (!['shopping-list-form', 'shopping-item-form'].includes(form.id)) return;
  event.preventDefault();
  const fields = Object.fromEntries(new FormData(form));
  if (form.id === 'shopping-list-form') {
    void saveShopping('/api/shopping/lists', 'POST', fields);
  } else if (editingShoppingItem) {
    const { id, version } = editingShoppingItem;
    void saveShopping(`/api/shopping/items/${encodeURIComponent(id)}`, 'PUT', { ...fields, expectedVersion: version });
  } else {
    void saveShopping(`/api/shopping/lists/${encodeURIComponent(shoppingList)}/items`, 'POST', fields);
  }
});

async function flushQueue(){if(!me||!navigator.onLine)return;const expectedUser=me.id;try{const session=await api('/api/me');if(session.status===401){await expireLocalSession();return}if(!session.ok)return;const data=await session.json();if(!data.user||data.user.id!==expectedUser){await expireLocalSession();return}csrf=data.csrf}catch{return}let changed=false;for(const operation of await queuedFor(expectedUser)){if(operation.nextAt>Date.now())continue;try{const r=await api(`/api/items/${encodeURIComponent(operation.itemId)}/complete`,{method:'POST',body:JSON.stringify({csrf,expectedVersion:operation.expectedVersion,mutationId:operation.mutationId})});if(r.status===401){await expireLocalSession();return}if(r.status===403){await removeQueued(operation.key);changed=true;setNotice('This account is not allowed to complete that task.',true);continue}if(r.status===404||r.status===409||r.status===422){await removeQueued(operation.key);changed=true;setNotice(r.status===409?'This task changed on another device. The household list has been refreshed.':r.status===422?'This task needs to be refreshed before it can sync.':'This task no longer exists.',r.status===422);continue}if(r.status>=500){if(operation.attempt>=2){await removeQueued(operation.key);changed=true;setNotice('The server could not save this task. Please try again.',true)}else{operation.attempt++;operation.nextAt=Date.now()+1000*(2**operation.attempt);await storeQueued(operation);setTimeout(flushQueue,operation.nextAt-Date.now())}continue}if(!r.ok){await removeQueued(operation.key);changed=true;continue}await removeQueued(operation.key);changed=true}catch{if(operation.attempt>=2){await removeQueued(operation.key);changed=true;setNotice('The task could not sync after several tries. Please complete it again.',true)}else{operation.attempt++;operation.nextAt=Date.now()+1000*(2**Math.min(operation.attempt,3));await storeQueued(operation);setTimeout(flushQueue,operation.nextAt-Date.now())}}}if(changed){offline=false;authState='authenticated';await loadData()}}
async function complete(id){const item=items.find(i=>i.id===id);if(!item)return;const original=item.completed,operation={key:`${me.id}:${crypto.randomUUID()}`,userId:me.id,itemId:item.id,expectedVersion:item.version,mutationId:crypto.randomUUID(),attempt:0,nextAt:0};item.completed=1;render();let response;try{response=await api(`/api/items/${encodeURIComponent(id)}/complete`,{method:'POST',body:JSON.stringify({csrf,expectedVersion:operation.expectedVersion,mutationId:operation.mutationId})})}catch{try{await storeQueued(operation)}catch{item.completed=original;setNotice('This device could not queue the change. Reconnect and try again.',true);return}offline=true;authState='offline-authorized';if(navigator.onLine)setTimeout(flushQueue,1000);setNotice('Completion is queued for this signed-in member. It will sync after reconnection.');return}if(response.status===401){item.completed=original;await expireLocalSession();return}if(response.status===403){item.completed=original;setNotice('This account is not allowed to complete that task.',true);return}if(response.status===404){items=items.filter(x=>x.id!==id);setNotice('That task no longer exists. The list has been refreshed.');render();return}if(response.status===409){item.completed=original;setNotice('This task changed on another device. Refreshing the household list.');await loadData();return}if(response.status===422){item.completed=original;const data=await response.json();setNotice(data.error||'Refresh this task before completing it.',true);render();return}if(response.status>=500){try{await storeQueued(operation)}catch{item.completed=original;setNotice('This device could not queue a retry. Please try again.',true);return}setTimeout(flushQueue,1000);setNotice('The server is temporarily unavailable. This completion will retry.');return}if(!response.ok){item.completed=original;setNotice('The task could not be completed.',true);return}const saved=await response.json();Object.assign(item,saved);offline=false;authState='authenticated';render()}
async function submitItem(form){const f=new FormData(form),kind=screen.slice(4),payload={kind,title:f.get('title'),details:f.get('details'),dueAt:f.get('dueAt'),assignedTo:f.get('assignedTo'),points:Number(f.get('points')||0),csrf};try{const r=await api('/api/items',{method:'POST',body:JSON.stringify(payload)}),data=await r.json();if(!r.ok)throw Error(data.error);screen=kind==='event'?'calendar':kind==='task'?'tasks':'more';message='Saved to your household.';await loadData()}catch(e){error=e.message||'Unable to save while offline.';render()}}
function addDefault(){const kind={today:'task',calendar:'event',tasks:'task',meals:'meal',shopping:'shopping',recipes:'recipe',inventory:'inventory',rewards:'reward',announcements:'announcement'}[screen]||'task';screen=`new:${kind}`;message='';render()}
app.addEventListener('click',async e=>{const nav=e.target.closest('[data-nav]'),act=e.target.closest('[data-action]'),check=e.target.closest('[data-complete]'),newKind=e.target.closest('[data-new-kind]');if(nav){quickOpen=false;screen=nav.dataset.nav;message='';error='';await loadData();return}if(newKind?.dataset.newKind==='event'){quickOpen=false;openCalendarForm();return}if(newKind?.dataset.newKind==='shopping'){quickOpen=false;screen='shopping';await loadData();return}if(newKind){quickOpen=false;screen=`new:${newKind.dataset.newKind}`;message='';render();return}if(check){await complete(check.dataset.complete);return}if(act?.dataset.action==='add'){quickOpen=!quickOpen;render();return}if(act?.dataset.action==='logout'){const leavingId=me.id;try{await api('/api/logout',{method:'POST',body:JSON.stringify({csrf})})}catch{}if(live){live.close();live=null}try{await clearQueued(leavingId)}catch{}clearLegacyCaches();resetShopping();me=null;csrf='';members=[];items=[];offline=false;authState='signed-out';screen='today';render();return}if(act?.dataset.action==='theme'){const cur=document.documentElement.dataset.theme||'system',next=cur==='system'?'light':cur==='light'?'dark':'system';applyTheme(next);return}});
app.addEventListener('submit',async e=>{if(e.target.id==='item-form'){e.preventDefault();await submitItem(e.target)}if(e.target.id==='member-form'){e.preventDefault();try{const payload=Object.fromEntries(new FormData(e.target));payload.csrf=csrf;const r=await api('/api/members',{method:'POST',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);message='Member added.';await loadData()}catch(err){error=err.message;render()}}if(e.target.id==='password-form'){e.preventDefault();try{const payload=Object.fromEntries(new FormData(e.target));payload.csrf=csrf;const r=await api('/api/password',{method:'POST',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);message='Password updated. Other sessions were signed out.';await loadData()}catch(err){error=err.message;render()}}});
function applyTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('hs-theme',theme);document.documentElement.style.colorScheme=theme==='system'?'light dark':theme}const savedTheme=localStorage.getItem('hs-theme')||'system';applyTheme(savedTheme);app.addEventListener('change',e=>{if(e.target.id==='theme-select')applyTheme(e.target.value)});
let sessionCheck=null;
async function revalidateSession(){if(sessionCheck)return sessionCheck;sessionCheck=(async()=>{try{const response=await api('/api/me');if(!response.ok){await expireLocalSession();return}const data=await response.json();if(!data.user||data.user.id!==me?.id){await expireLocalSession();return}csrf=data.csrf;offline=false;authState='authenticated'}catch{if(me){offline=true;authState='offline-authorized'}if(!formHasDraft())render()}})();try{await sessionCheck}finally{sessionCheck=null}}
function startLive(){if(!me||!navigator.onLine||!window.EventSource)return;if(live&&live.readyState!==2)return;live=new EventSource('/api/events');live.addEventListener('open',()=>{offline=false;authState='authenticated';if(!formHasDraft())render();loadData()});live.addEventListener('household-change',()=>loadData());live.addEventListener('error',()=>{revalidateSession()})}
window.addEventListener('online',()=>{startLive();flushQueue()});window.addEventListener('offline',()=>{offline=!!me;if(me)authState='offline-authorized';if(!formHasDraft())render()});if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
(async()=>{try{const state=await fetch('/api/setup-state').then(r=>r.json());if(!state.initialized){renderAuth(true);return}const r=await api('/api/me');if(!r.ok)throw Error();const d=await r.json();if(d.user){me=d.user;csrf=d.csrf;authState='authenticated';await loadData();startLive()}else{authState='signed-out';renderAuth(false)}}catch{me=null;members=[];items=[];offline=false;authState='signed-out';error='Household server is unavailable. Connect to your local network and sign in to continue.';renderAuth(false)}})();

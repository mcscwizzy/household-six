import { allowanceView, habitForm, habitsView } from './members-life.js';
import { announcementsView, announcementForm, wallView } from './announcements.js';
import { inventoryForm, inventoryView } from './inventory.js';
import { sixView } from './six.js';
import { ingredientFields, mealForm, mealView, recipeForm, recipesView } from './meals.js';
import { choreCard, choreForm, choresView } from './chores.js';
import { rewardForm, rewardsView } from './rewards.js';
import { dashboardView } from './dashboard.js';
import { calendarForm, calendarView, moveCalendar, rangeFor } from './calendar.js';
import { householdDate, shiftDay } from './dates.js';
import { shoppingView } from './shopping.js';
import { escapeHtml as esc } from './html.js';
import { clearLegacyCaches, clearQueued, queuedFor, removeQueued, storeQueued } from './offline.js';
import { maintenanceCompleteForm, maintenanceForm, maintenanceView, vehicleForm, vehiclesView, vehicleServiceForm } from './property-care.js';
const $=s=>document.querySelector(s);const app=$('#app');
const SIGNED_OUT = 'hs-explicit-signout';
const modules={today:['Today','☀️'],calendar:['Calendar','▦'],tasks:['Chores','✓'],meals:['Meals','♨'],more:['More','⌘'],shopping:['Shopping lists','🛒'],recipes:['Recipes','🍲'],inventory:['Pantry & freezer','🥕'],rewards:['Rewards','⭐'],announcements:['Announcements','📌'],habits:['Habits','◉'],allowance:['Allowance','$'],maintenance:['Maintenance','⌂'],vehicles:['Vehicles','🚗']};
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
let choreData = null;
let choreDay = null;
let rewardData = null;
let domainDraft = null;
let domainSaving = false;
let mealData = null;
let recipeData = null;
let mealDate = null;
let groceryList = 'default';
let sixData = null;
let sixPoll = null;
let inventoryData = null;
let inventoryLocation = '';
let renderedScreen = null;
let renderedMarkup = null;
let refreshTimer = null;
let latestInteraction = 0;
let queueReplay = null;
let announcementData = null;
let showExpired = false;
let habitsData = null;
let allowanceData = null;
let sessionsData = null;
let memberSessionsData = {};
let propertyCareData = null;




function resetPrivateViews() {
  habitsData = null;
  allowanceData = null;
  sessionsData = null;
  memberSessionsData = {};
  propertyCareData = null;
  announcementData = null;
  showExpired = false;
  inventoryData = null;
  inventoryLocation = '';
  renderedScreen = null;
  renderedMarkup = null;
  clearTimeout(refreshTimer);
  sixData = null;
  clearTimeout(sixPoll);
  mealData = null;
  recipeData = null;
  mealDate = null;
  groceryList = 'default';
  choreData = null;
  choreDay = null;
  rewardData = null;
  domainDraft = null;
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

async function expireLocalSession(){const expiredId=me?.id;if(expiredId)try{await clearQueued(expiredId)}catch{}clearLegacyCaches();resetPrivateViews();me=null;csrf='';members=[];items=[];offline=false;authState='signed-out';if(live){live.close();live=null}renderAuth(false)}
clearLegacyCaches();
function formHasDraft(){
  if (['calendar-form', 'chore-form', 'reward-form', 'meal-form', 'recipe-form','inventory-form','announcement-form','habit-form','maintenance-form','vehicle-form','vehicle-service-form'].includes(screen) || document.querySelector('#calendar-import input')?.files?.length) return true;
  if (['members', 'settings'].includes(screen) && document.activeElement?.closest('form[data-profile-id],form[data-member-reset],#profile-form,#password-form')) return true;
  if (screen === 'allowance' && document.activeElement?.closest('#allowance-form')) return true;
  if (screen === 'inventory' && document.activeElement?.closest('.inventory-stock-form')) return true;
  if (screen === 'six' && document.activeElement?.closest('#six-form')) return true;
  const shoppingForm = document.activeElement?.closest('#shopping-item-form, #shopping-list-form');
  if (shoppingForm || editingShoppingItem) return screen === 'shopping';
if(!screen.startsWith('new:'))return false;const form=$('#item-form');return !!form&&(form.contains(document.activeElement)||Array.from(new FormData(form).values()).some(Boolean))}
function setNotice(text,isError=false){message=isError?'':text;error=isError?text:'';render()}
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(options.method&&options.method!=='GET'&&csrf)headers['X-CSRF-Token']=csrf;return fetch(path,{...options,headers,credentials:'same-origin'})}
function navButton(id,side=false){const [name,icon]=modules[id];return `<button class="${side?'side-button':'nav-item'} ${screen===id?'active':''}" data-nav="${id}">${side?`<span>${icon}</span><span>${name}</span>`:`<span class="nav-icon">${icon}</span><span>${name==='Shopping lists'?'Lists':name}</span>`}</button>`}
function shell(content){return `<div class="shell"><aside class="side"><div class="side-brand"><img src="/logo.svg" alt=""><span>Household Six</span></div>${['today','calendar','tasks','meals','more'].map(x=>navButton(x,true)).join('')}<div class="side-spacer"></div><button class="side-button" data-action="theme">◐ <span>Appearance</span></button></aside><header class="topbar"><div class="brand"><img src="/logo.svg" alt=""><span>Household Six</span></div><div class="top-actions"><span class="connection ${offline?'offline':''}">${authState==='offline-authorized'?'Offline authorized · changes pending':'● Local & private'}</span><button class="theme" data-action="theme" aria-label="Toggle appearance">◐</button></div></header><main class="main">${message?`<div class="notice">${esc(message)}</div>`:''}${error?`<div class="notice error">${esc(error)}</div>`:''}${content}<p class="footer-note">Your household. Your hardware. Your data.</p></main><nav class="bottom-nav" aria-label="Main navigation">${['today','calendar','tasks','meals','more'].map(x=>navButton(x)).join('')}</nav>${!['shopping','calendar','calendar-form','chore-form','reward-form','rewards','meal-form','recipe-form','meals','recipes','six','inventory','inventory-form','announcement-form','announcements','habit-form','habits','allowance','maintenance','maintenance-form','vehicles','vehicle-form','vehicle-service-form'].includes(screen)&&canCreateKind(screen==='tasks'?'task':screen==='events'?'event':screen)?'<button class="quick" data-action="add" aria-label="Add item">+</button>':''}${quickOpen?quickMenu():''}</div>`}
function memberChips(balances){return `<div class="member-row">${balances.map(m=>`<div class="member"><span class="avatar color-${avatarColor(m.color)}">${esc(m.display_name.slice(0,1).toUpperCase())}</span>${esc(m.display_name)}${` · ${m.points} pts`}</div>`).join('')}</div>`}
function avatarColor(color){return ({'#233C32':'forest','#78937D':'sage','#C69A5D':'gold','#54768C':'blue','#9B6B72':'rose','#7B6C9B':'violet'})[color]||'sage'}
function canCreateKind(kind){if(!me||me.role==='display')return false;if(['owner','admin','adult'].includes(me.role))return true;return me.role==='child'&&['task','shopping'].includes(kind)}
function quickMenu(){const choices=[['task','Task'],['chore','Chore'],['event','Calendar event'],['shopping','Shopping item'],['meal','Meal'],['inventory','Inventory item'],['recipe','Recipe'],['reward','Reward'],['announcement','Announcement']].filter(([kind])=>canCreateKind(kind === 'chore' ? 'event' : kind));return `<div class="quick-menu card" role="group" aria-label="Quick add">${choices.map(([kind,label])=>`<button class="quick-choice" data-new-kind="${kind}">${label}</button>`).join('')}</div>`}
function itemCard(item){const who=item.assigned_name||members.find(m=>m.id===item.assigned_to)?.display_name;const completable=['task','shopping'].includes(item.kind);const label={event:'Scheduled',meal:'Planned',inventory:'In stock',recipe:'Saved',reward:'Available',announcement:'Posted'}[item.kind]||'Saved';const control=me.role==='display'?`<span class="badge">${item.completed?'Done':'Read only'}</span>`:completable?`<button class="check ${item.completed?'done':''}" data-complete="${esc(item.id)}" aria-label="${item.completed?'Completed':'Complete'} ${esc(item.title)}">${item.completed?'✓':''}</button>`:`<span class="badge">${item.completed?'Done':label}</span>`;return `<article class="card row item-card ${item.completed?'completed':''}">${control}<div class="item-main"><div class="item-title">${esc(item.title)}</div><div class="item-detail">${esc(item.details||item.due_at||'')}${who?' · '+esc(who):''}</div></div>${item.value?`<span class="badge">⭐ ${item.value}</span>`:''}</article>`}
function moreView(){const tiles=['shopping','recipes','inventory','rewards','announcements',...(me.role === 'display' ? [] : ['habits','allowance']),...(['owner','admin','adult'].includes(me.role)?['maintenance','vehicles']:[])];return `<div class="greeting"><div><div class="eyebrow">Your family toolkit</div><h1>More</h1><div class="subtle">Everything the household shares.</div></div></div><div class="more-grid">${tiles.map(id=>`<button class="card more-tile" data-nav="${id}"><span class="tile-icon">${modules[id][1]}</span><strong>${modules[id][0]}</strong><span class="item-detail">Open shared ${modules[id][0].toLowerCase()}</span></button>`).join('')}${['owner','admin','adult'].includes(me.role)?'<button class="card more-tile" data-nav="six"><span class="tile-icon">✦</span><strong>Six</strong><span class="item-detail">Local assistant</span></button>':''}<button class="card more-tile" data-nav="members"><span class="tile-icon">👨‍👩‍👧</span><strong>Members</strong><span class="item-detail">Household profiles</span></button><button class="card more-tile" data-nav="wall"><span class="tile-icon">▦</span><strong>Household display</strong><span class="item-detail">Clock and family schedule</span></button><button class="card more-tile" data-nav="settings"><span class="tile-icon">⚙️</span><strong>Settings</strong><span class="item-detail">Account and privacy</span></button></div>`}
function formView(kind){const label={task:'Task',event:'Calendar event',shopping:'Shopping item',meal:'Meal',inventory:'Inventory item',recipe:'Recipe',reward:'Reward',announcement:'Announcement'}[kind]||'Item';return `<div class="greeting"><div><div class="eyebrow">${esc(me.household)}</div><h1>Add ${label.toLowerCase()}</h1><div class="subtle">Your change is saved to your household server.</div></div></div><form class="card form-card form" id="item-form"><label class="field">Title<input name="title" maxlength="120" required autofocus placeholder="${kind==='shopping'?'e.g. Milk':'What would you like to add?'}"></label><label class="field">Notes<textarea name="details" maxlength="1000" placeholder="Add a helpful note (optional)"></textarea></label>${['task','event','meal','inventory'].includes(kind)?`<label class="field">${kind==='event'?'Date and time':'Date'}<input name="dueAt" type="${kind==='event'?'datetime-local':'date'}"></label>`:''}${kind==='task'&&me.role!=='child'?`<label class="field">Assign to<select name="assignedTo"><option value="">Anyone</option>${members.map(m=>`<option value="${esc(m.id)}">${esc(m.display_name)}</option>`).join('')}</select></label><label class="field">Points for completion<input type="number" name="points" min="0" max="10000" value="0"></label>`:''}<div class="actions"><button class="primary" type="submit">Save ${label.toLowerCase()}</button><button class="secondary" type="button" data-nav="${kind==='event'?'calendar':kind==='task'?'tasks':'more'}">Cancel</button></div></form>`}
function avatarChoices(selected='person'){const options={person:'Person',fox:'Fox',bear:'Bear',rabbit:'Rabbit',sun:'Sun',leaf:'Leaf',star:'Star'};return Object.entries(options).map(([id,label])=>`<option value="${id}" ${id===selected?'selected':''}>${label}</option>`).join('')}
function memberProfileForm(member){return `<form class="card form" data-profile-id="${esc(member.id)}"><label class="field">Name<input name="displayName" maxlength="70" value="${esc(member.display_name)}" required></label><label class="field">Member color<select name="color">${[['#78937D','Sage'],['#233C32','Forest'],['#C69A5D','Gold'],['#54768C','Blue'],['#9B6B72','Rose'],['#7B6C9B','Violet']].map(([value,label])=>`<option value="${value}" ${member.color===value?'selected':''}>${label}</option>`).join('')}</select></label><label class="field">Avatar<select name="avatar">${avatarChoices(member.avatar_key)}</select></label><button class="secondary">Save profile</button></form>`}
function memberSessionsPanel(member){const sessions=memberSessionsData[member.id];return `<details data-panel="member-sessions-${esc(member.id)}"><summary>Device sessions</summary><button class="secondary" type="button" data-member-sessions="${esc(member.id)}">Load active sessions</button>${Array.isArray(sessions)?sessions.length?`<div class="list">${sessions.map(session=>`<article class="card row"><div class="item-main"><strong>${esc(session.deviceName)}${session.current?' · This device':''}</strong><div class="item-detail">Started ${esc(session.createdAt.slice(0,16))} · Expires ${esc(session.expiresAt.slice(0,10))}</div></div><button class="secondary" data-session-revoke="${esc(session.id)}">Revoke</button></article>`).join('')}</div>`:'<p class="empty">No active sessions found.</p>':''}</details>`}
function memberView(){const admin=['owner','admin'].includes(me.role);const manage=m=>m.id!==me.id&&m.role!=='owner'&&(me.role==='owner'||['adult','child','display'].includes(m.role));return `<div class="greeting"><div><div class="eyebrow">Household profiles</div><h1>Members</h1><div class="subtle">Profiles stay inside this household.</div></div></div><div class="list">${members.map(m=>`<article class="card domain-row"><div class="row"><span class="avatar color-${avatarColor(m.color)}">${m.avatar_key==='person'?esc(m.display_name[0]):({fox:'🦊',bear:'🐻',rabbit:'🐰',sun:'☀️',leaf:'🍃',star:'⭐'}[m.avatar_key]||esc(m.display_name[0]))}</span><div class="item-main"><div class="item-title">${esc(m.display_name)} ${m.disabled_at?'<span class="badge">Disabled</span>':''}</div><div class="item-detail">${esc(m.role)}</div></div></div><details data-panel="member-profile-${esc(m.id)}"><summary>Edit profile</summary>${(m.id===me.id||admin&&manage(m))?memberProfileForm(m):'<p class="item-detail">Only you or an authorized household administrator can edit this profile.</p>'}</details>${manage(m)?`<div class="actions"><button type="button" class="secondary" data-account-status="${esc(m.id)}" data-active="${m.disabled_at?'false':'true'}">${m.disabled_at?'Reactivate account':'Disable account'}</button></div><details data-panel="member-reset-${esc(m.id)}"><summary>Reset password</summary><form class="card form" data-member-reset="${esc(m.id)}"><label class="field">New password<input name="newPassword" type="password" minlength="12" maxlength="200" autocomplete="new-password" required></label><button class="secondary">Reset password and sign out devices</button></form></details>${memberSessionsPanel(m)}`:''}</article>`).join('')}</div>${admin?`<div class="section-head"><h2>Add a member</h2></div><form id="member-form" class="card form"><label class="field">Name<input name="displayName" required></label><label class="field">Username<input name="username" minlength="3" required></label><label class="field">Role<select name="role">${(me.role==='owner'?['admin','adult','child','display']:['adult','child','display']).map(role=>`<option value="${role}">${role==='admin'?'Administrator':role==='child'?'Child profile':role==='display'?'Read-only display':'Adult'}</option>`).join('')}</select></label><label class="field">Member color<select name="color">
  <option value="#78937D">Sage</option><option value="#233C32">Forest</option>
  <option value="#C69A5D">Gold</option><option value="#54768C">Blue</option>
  <option value="#9B6B72">Rose</option><option value="#7B6C9B">Violet</option></select></label>
  <label class="field">Password (required to sign in; 12+ characters)<input name="password" type="password" minlength="12"></label><button class="primary">Add household member</button></form>`:''}`}
function settingsView(){return `<div class="greeting"><div><div class="eyebrow">Account</div><h1>Settings</h1><div class="subtle">Signed in as ${esc(me.displayName)} (${esc(me.role)}).</div></div></div><div class="card form"><div><strong>${esc(me.household)}</strong><div class="item-detail">Timezone: ${esc(me.timezone)}</div></div><label class="field">Appearance<select id="theme-select"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><details><summary>My profile</summary>${memberProfileForm({id:me.id,display_name:me.displayName,color:me.color,avatar_key:me.avatar||'person'})}</details><form id="password-form" class="form"><div class="section-head"><h2>Change password</h2></div><label class="field">Current password<input type="password" name="currentPassword" required autocomplete="current-password"></label><label class="field">New password<input type="password" name="newPassword" minlength="12" required autocomplete="new-password"></label><button class="primary">Update password</button></form><button class="secondary" data-action="logout">Sign out</button><div class="item-detail">Your local household server holds your account and family data. No analytics or cloud account is used.</div></div><div class="section-head"><h2>Active sessions</h2></div><div class="list">${sessionsData?.length?sessionsData.map(session=>`<article class="card row"><div class="item-main"><strong>${esc(session.deviceName)}${session.current?' · This device':''}</strong><div class="item-detail">Started ${esc(session.createdAt.slice(0,16))} · Expires ${esc(session.expiresAt.slice(0,10))}</div></div><button class="secondary" data-session-revoke="${esc(session.id)}">Revoke</button></article>`).join(''):'<p class="empty">No active sessions found.</p>'}</div>`}
function render(){if(!me){renderAuth();return}
  if (screen === 'wall') {
    renderedScreen = 'wall';
    const next = wallView(dashboardData, announcementData, me.household, me.timezone);
    if (next !== renderedMarkup) app.innerHTML = next;
    renderedMarkup = next;
    return;
  }
  const expanded = renderedScreen === screen
    ? new Set([...app.querySelectorAll('details[data-panel][open]')].map(panel => panel.dataset.panel))
    : new Set();
  renderedScreen = screen;
  let content=screen==='today'?dashboardView(dashboardData, me.household, canCreateKind('task'),
    entry => entry.choreId ? choreCard(entry, me.role !== 'display') : itemCard(entry), memberChips):screen==='calendar'?calendarView(calendarData, calendarState, members, canCreateKind('event'))
  :screen==='calendar-form'?calendarForm(calendarDraft, members, calendarState.anchor, calendarOccurrence, calendarAllDay):screen==='tasks'?choresView(choreData, choreDay, householdDate(me.timezone), me.role, items, itemCard)
  :screen==='chore-form'?choreForm(domainDraft, members, householdDate(me.timezone))
  :screen==='reward-form'?rewardForm(domainDraft):screen==='meals'?mealView(mealData, canCreateKind('meal'), groceryList):screen==='more'?moreView():screen==='six'?sixView(sixData):screen==='members'?memberView():screen==='settings'?settingsView():screen==='shopping'?shoppingView(shoppingData, {
  canEdit: canCreateKind('shopping'), canCreateList: ['owner', 'admin', 'adult'].includes(me.role),
  mode: shoppingMode, editing: editingShoppingItem,
}):screen==='recipes'?recipesView(recipeData, canCreateKind('recipe')):screen==='inventory'?inventoryView(inventoryData, inventoryLocation, canCreateKind('inventory')):screen==='rewards'?rewardsView(rewardData, me.role, me.id)
  :screen==='inventory-form'?inventoryForm(domainDraft, inventoryLocation)
  :screen==='meal-form'?mealForm(domainDraft, recipeData || [], mealDate || householdDate(me.timezone))
  :screen==='recipe-form'?recipeForm(domainDraft):screen==='announcements'?announcementsView(announcementData,me.role,showExpired)
  :screen==='announcement-form'?announcementForm(domainDraft)
  :screen==='habits'?habitsView(habitsData)
  :screen==='habit-form'?habitForm(domainDraft, members, canCreateKind('reward'), me.id)
  :screen==='allowance'?allowanceView(allowanceData, canCreateKind('reward')):screen==='maintenance'?maintenanceView(propertyCareData,members,['owner','admin','adult'].includes(me.role))
  :screen==='maintenance-form'?maintenanceForm(domainDraft,members,propertyCareData?.templates)
  :screen==='maintenance-complete-form'?maintenanceCompleteForm(domainDraft,householdDate(me.timezone))
  :screen==='vehicles'?vehiclesView(propertyCareData,['owner','admin','adult'].includes(me.role))
  :screen==='vehicle-form'?vehicleForm(domainDraft)
  :screen==='vehicle-service-form'?vehicleServiceForm(domainDraft?.vehicle,domainDraft?.service)
  :screen.startsWith('new:')?formView(screen.slice(4)):'';
const next = shell(content);
if (next === renderedMarkup) return;
renderedMarkup = next;
app.innerHTML = next;
for (const panel of app.querySelectorAll('details[data-panel]')) {
  if (expanded.has(panel.dataset.panel)) panel.open = true;
}
const themeSelect=$('#theme-select');if(themeSelect)themeSelect.value=localStorage.getItem('hs-theme')||'system';}
function renderAuth(setup=false){renderedMarkup=null;app.innerHTML=`<main class="auth"><section class="card auth-card"><div class="auth-brand"><img src="/logo.svg" alt=""><div><h1>Household Six</h1><p>Your household. Your hardware. Your data.</p></div></div>${error?`<div class="notice error">${esc(error)}</div>`:''}<form class="form" id="auth-form">${setup?`<label class="field">Household name<input name="household" required maxlength="70" placeholder="The Johnson Family"></label><label class="field">Your name<input name="displayName" required maxlength="70"></label>`:''}<label class="field">Username<input name="username" required minlength="3" autocomplete="username"></label><label class="field">Password<input name="password" type="password" required minlength="${setup?12:1}" autocomplete="${setup?'new-password':'current-password'}">${setup?'<span class="item-detail">Use at least 12 characters. This account is the local owner.</span>':''}</label><button class="primary">${setup?'Create household':'Sign in'}</button></form><p class="footer-note">Stored on your household server. No account with an outside service is needed.</p></section></main>`;$('#auth-form').addEventListener('submit',authSubmit)}
async function authSubmit(event){event.preventDefault();const f=new FormData(event.currentTarget),setup=!!f.get('household');try{const res=await fetch(setup?'/api/setup':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(Object.fromEntries(f))});const data=await res.json();if(!res.ok)throw Error(data.error);localStorage.removeItem(SIGNED_OUT);me=data.user;csrf=data.csrf;authState='authenticated';if(me.role==='display')screen='wall';await loadData();startLive();}catch(e){error=e.message||'Could not reach your household server.';renderAuth(setup)}}
async function loadData({ background = false } = {}) {
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
  if (!choreDay) choreDay = householdDate(me.timezone);
  if (!mealDate) mealDate = householdDate(me.timezone);
  const paths = ['/api/members', '/api/summary', ...(view === 'wall'
    ? ['/api/dashboard','/api/announcements'] : view === 'announcements'
    ? [`/api/announcements?include_expired=${showExpired}`] : view === 'today' ? ['/api/dashboard'] : view === 'calendar'
    ? [`/api/calendar?${calendarQuery}`] : view === 'shopping'
    ? [`/api/shopping?list=${encodeURIComponent(shoppingList)}`] : view === 'tasks'
    ? [`/api/chores?date=${encodeURIComponent(choreDay)}`, '/api/items?kind=task'] : view === 'rewards'
    ? ['/api/rewards'] : view === 'meals' ? [`/api/meals?date=${encodeURIComponent(mealDate)}`]
    : view === 'recipes' ? ['/api/recipes'] : view === 'six' ? ['/api/six']
    : view === 'habits' ? ['/api/habits'] : view === 'allowance' ? ['/api/allowance']
    : view === 'inventory' ? [`/api/inventory?location=${encodeURIComponent(inventoryLocation)}`]
    : view === 'maintenance' || view === 'vehicles' ? ['/api/maintenance']
    : view === 'settings' ? ['/api/sessions'] : kinds.map(kind => `/api/items?kind=${kind}`))];
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
    if (background && performance.now() - latestInteraction < 350) {
      scheduleLiveRefresh();
      return;
    }
    members = directory.members.map(member => ({
      ...member, points: summary.members.find(entry => entry.id === member.id)?.points || 0,
    }));
    if (view === 'wall') {
      [dashboardData, announcementData] = records;
      items = [];
    } else if (view === 'announcements') {
      [announcementData] = records;
      items = [];
    } else if (view === 'today') {
      dashboardData = records[0];
      items = [...dashboardData.chores, ...dashboardData.overdue, ...dashboardData.unscheduled];
    } else if (view === 'calendar') {
      calendarData = records[0];
      items = [];
    } else if (view === 'habits') {
      [habitsData] = records;
      items = [];
    } else if (view === 'allowance') {
      [allowanceData] = records;
      items = [];
    } else if (view === 'settings') {
      [sessionsData] = [records[0]?.sessions || []];
      items = [];
    } else if (view === 'inventory') {
      [inventoryData] = records;
      items = [];
    } else if (view === 'maintenance' || view === 'vehicles') {
      [propertyCareData] = records;
      items = [];
    } else if (view === 'six') {
      [sixData] = records;
      items = [];
      clearTimeout(sixPoll);
      if (sixData.jobs.some(job => ['queued', 'running'].includes(job.state))) {
        sixPoll = setTimeout(() => { if (screen === 'six') void loadData(); }, 2500);
      }
    } else if (view === 'meals') {
      [mealData] = records;
      recipeData = mealData.recipes;
      items = [];
    } else if (view === 'recipes') {
      recipeData = records[0].recipes;
      items = [];
    } else if (view === 'tasks') {
      [choreData] = records;
      items = records[1].items;
    } else if (view === 'rewards') {
      [rewardData] = records;
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
    ...fields, allDay: calendarAllDay, rule, timezone: calendarDraft?.timezone,
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
    const { id, title, details, start, end, allDay, assignedTo, rule, version, exceptions, timezone } = calendarDraft;
    void saveCalendar(`/api/calendar/${encodeURIComponent(id)}`, 'PUT', {
      title, details, start, end, allDay, assignedTo: assignedTo || '', rule, timezone, expectedVersion: version,
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

function openDomainForm(kind, draft = null) {
  domainDraft = draft;
  screen = `${kind}-form`;
  quickOpen = false;
  message = '';
  error = '';
  render();
}

async function saveDomain(path, method, fields, success, destination = screen) {
  if (domainSaving) return;
  domainSaving = true;
  const userId = me?.id;
  const view = screen;
  try {
    const response = await api(path, {
      method, body: JSON.stringify({ ...fields, csrf, mutationId: crypto.randomUUID() }),
    });
    if (me?.id !== userId || screen !== view) return;
    if (response.status === 401) return expireLocalSession();
    const result = response.status === 204 ? null : await response.json();
    if (!response.ok) throw Error(result.error || 'The change could not be saved.');
    screen = destination;
    domainDraft = null;
    message = typeof success === 'function' ? success(result) : success;
    error = '';
    await loadData();
  } catch (err) {
    if (me?.id === userId && screen === view) showFormError(err instanceof TypeError ? 'Reconnect to save this change.' : err.message);
  } finally {
    domainSaving = false;
  }
}

app.addEventListener('click', event => {
  const controls = event.target.closest('button')?.dataset;
  if (!controls || !me) return;
  const enc = encodeURIComponent;
  if (controls.domainOpen) return openDomainForm(controls.domainOpen);
  if (controls.choreStep) {
    choreDay = controls.choreStep === '0' ? householdDate(me.timezone) : shiftDay(choreDay, Number(controls.choreStep));
    void loadData();
  }
  if (controls.choreEdit) {
    const selected = choreData?.templates.find(entry => entry.id === controls.choreEdit);
    if (selected) openDomainForm('chore', selected);
  }
  if ('choreArchive' in controls && domainDraft && window.confirm('Archive this chore schedule?')) {
    void saveDomain(`/api/chores/${enc(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Chore schedule archived.', 'tasks');
  }
  if (controls.choreComplete) {
    const selected = [...(choreData?.scheduled || []), ...(dashboardData?.scheduledChores || []),
      ...(dashboardData?.scheduledOverdue || [])].find(entry => entry.id === controls.choreComplete);
    if (selected) void saveDomain(`/api/chores/${enc(selected.choreId)}/complete`, 'POST',
      { expectedVersion: selected.version, date: selected.date, assignedTo: selected.assignedTo, expectedScheduleVersion: selected.scheduleVersion },
      selected.approvalRequired ? 'Sent for approval.' : 'Chore completed.');
  }
  if (controls.choreReview) {
    const selected = choreData.history.find(entry => entry.id === controls.choreReview);
    if (selected) void saveDomain(`/api/chores/occurrences/${enc(selected.id)}/review`, 'POST',
      { expectedVersion: selected.version, approved: controls.approve === 'true' }, 'Chore reviewed.');
  }
  if (controls.rewardEdit) {
    const selected = [...rewardData.rewards, ...rewardData.legacy].find(entry => entry.id === controls.rewardEdit);
    if (selected) openDomainForm('reward', selected);
  }
  if ('rewardArchive' in controls && domainDraft && window.confirm('Archive this reward?')) {
    void saveDomain(`/api/rewards/${enc(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Reward archived.', 'rewards');
  }
  if (controls.rewardRequest) {
    const selected = rewardData.rewards.find(entry => entry.id === controls.rewardRequest);
    if (selected) void saveDomain(`/api/rewards/${enc(selected.id)}/request`, 'POST',
      { expectedVersion: selected.version }, 'Reward requested.');
  }
  if (controls.rewardReview) {
    const selected = rewardData.requests.find(entry => entry.id === controls.rewardReview);
    if (selected) void saveDomain(`/api/rewards/redemptions/${enc(selected.id)}/review`, 'POST',
      { expectedVersion: selected.version, approved: controls.approve === 'true' }, 'Redemption reviewed.');
  }
});

app.addEventListener('change', event => {
  if (event.target.id === 'chore-date' && event.target.value) {
    choreDay = event.target.value;
    void loadData();
  }
});

app.addEventListener('submit', event => {
  const form = event.target;
  if (!['chore-form', 'reward-form'].includes(form.id)) return;
  event.preventDefault();
  const source = new FormData(form);
  const fields = { ...Object.fromEntries(source), points: Number(source.get('points')), expectedVersion: domainDraft?.version };
  const isChore = form.id === 'chore-form';
  if (isChore) {
    fields.approvalRequired = source.has('approvalRequired');
    fields.assignees = source.getAll('assignees');
  }
  const base = isChore ? '/api/chores' : '/api/rewards';
  const path = domainDraft ? `${base}/${encodeURIComponent(domainDraft.id)}` : base;
  void saveDomain(path, domainDraft ? 'PUT' : 'POST', fields, isChore ? 'Chore saved.' : 'Reward saved.',
    isChore ? 'tasks' : 'rewards');
});

async function openMeal(draft = null) {
  const userId = me?.id;
  const view = screen;
  if (!recipeData) {
    try {
      const response = await api('/api/recipes');
      if (me?.id !== userId || screen !== view) return;
      if (response.status === 401) return expireLocalSession();
      if (!response.ok) throw Error('Recipes could not be loaded.');
      const data = await response.json();
      if (me?.id !== userId || screen !== view) return;
      recipeData = data.recipes;
    } catch (err) {
      if (me?.id === userId && screen === view) showFormError(err.message);
      return;
    }
  }
  openDomainForm('meal', draft);
}

app.addEventListener('click', event => {
  const actions = event.target.closest('button')?.dataset;
  if (!actions || !me) return;
  if (actions.mealDate) void openMeal({ day: actions.mealDate, slot: actions.mealSlot });
  if (actions.mealStep) {
    mealDate = actions.mealStep === '0' ? householdDate(me.timezone) : shiftDay(mealDate, Number(actions.mealStep));
    void loadData();
  }
  if (actions.mealEdit) {
    const selected = mealData.meals.find(item => item.id === actions.mealEdit);
    if (selected) void openMeal(selected);
  }
  if (actions.recipeEdit) {
    const selected = recipeData.find(item => item.id === actions.recipeEdit);
    if (selected) openDomainForm('recipe', selected);
  }
  if (actions.recipePlan) {
    const selected = recipeData.find(item => item.id === actions.recipePlan);
    if (selected) void openMeal({ recipe_id: selected.id, servings: selected.servings });
  }
  if ('mealArchive' in actions && domainDraft?.id && window.confirm('Remove this meal from the plan?')) {
    void saveDomain(`/api/meals/${encodeURIComponent(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Meal removed.', 'meals');
  }
  if ('recipeArchive' in actions && domainDraft?.id && window.confirm('Archive this recipe?')) {
    void saveDomain(`/api/recipes/${encodeURIComponent(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Recipe archived.', 'recipes');
  }
  const ingredientList = document.querySelector('#ingredient-list');
  if ('ingredientAdd' in actions && ingredientList && ingredientList.childElementCount < 60) {
    ingredientList.insertAdjacentHTML('beforeend', ingredientFields());
    ingredientList.lastElementChild.querySelector('input').focus();
  }
  if ('ingredientRemove' in actions && ingredientList?.childElementCount > 1) {
    event.target.closest('.ingredient-fields')?.remove();
  }
});

app.addEventListener('input', event => {
  const scale = event.target.dataset.recipeScale;
  const requested = Number(event.target.value);
  if (!scale || !Number.isInteger(requested) || requested < 1 || requested > 1000) return;
  for (const quantity of event.target.closest('.recipe-card').querySelectorAll('[data-base-quantity]')) {
    quantity.textContent = (Number(quantity.dataset.baseQuantity) * requested / Number(scale))
      .toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
});

app.addEventListener('change', event => {
  if (event.target.form?.id === 'grocery-sync-form') groceryList = event.target.value;
  if (event.target.name === 'recipeId' && event.target.form?.id === 'meal-form') {
    const count = event.target.selectedOptions[0]?.dataset.servings;
    if (count) event.target.form.elements.servings.value = count;
  }
});

app.addEventListener('submit', event => {
  const form = event.target;
  if (!['meal-form', 'recipe-form', 'grocery-sync-form'].includes(form.id)) return;
  event.preventDefault();
  const source = new FormData(form);
  if (form.id === 'grocery-sync-form') {
    void saveDomain('/api/meals/groceries', 'POST', { date: mealData.weekStart, listId: source.get('listId') },
      result => `Groceries synced. ${result.created} added, ${result.updated} updated, ${result.removed} removed.`);
    return;
  }
  const isRecipe = form.id === 'recipe-form';
  const fields = {
    title: source.get('title'), details: source.get('details'), servings: Number(source.get('servings')),
    expectedVersion: domainDraft?.version,
  };
  if (isRecipe) {
    fields.instructions = source.get('instructions');
    fields.ingredients = [...form.querySelectorAll('.ingredient-fields')].map(row =>
      Object.fromEntries([...row.querySelectorAll('input')].map(input => [input.name, input.value])));
  } else {
    Object.assign(fields, { date: source.get('date'), slot: source.get('slot'), recipeId: source.get('recipeId') });
  }
  const base = isRecipe ? '/api/recipes' : '/api/meals';
  const path = domainDraft?.id ? `${base}/${encodeURIComponent(domainDraft.id)}` : base;
  if (!isRecipe) mealDate = fields.date;
  void saveDomain(path, domainDraft?.id ? 'PUT' : 'POST', fields, isRecipe ? 'Recipe saved.' : 'Meal saved.',
    isRecipe ? 'recipes' : 'meals');
});

app.addEventListener('change', event => {
  if (event.target.form?.id === 'six-form' && event.target.name === 'kind') {
    const fields = document.querySelector('#six-attachment-field');
    fields.hidden = !['recipe','document'].includes(event.target.value);
    if (fields.hidden) fields.querySelector('input').value = '';
  }
});

app.addEventListener('click', event => {
  const control = event.target.closest('[data-six-decision], [data-six-refresh]');
  if (!control || !me) return;
  if ('sixRefresh' in control.dataset) {
    void loadData();
    return;
  }
  const job = sixData?.jobs.find(entry => entry.id === control.dataset.sixDecision);
  if (job) void saveDomain(`/api/six/${encodeURIComponent(job.id)}/decision`, 'POST',
    { expectedVersion: job.version, confirm: control.dataset.sixConfirm === 'true' }, 'Proposal reviewed.');
});

app.addEventListener('submit', async event => {
  const form = event.target;
  if (form.id !== 'six-form') return;
  event.preventDefault();
  const source = new FormData(form);
  const kind = source.get('kind');
  const text = source.get('text');
  const file = form.elements.attachment.files[0];
  const payload = { kind, text };
  if (file) {
    if (file.size > 550000) {
      showFormError('Choose a document or image under 550 KB.');
      return;
    }
    try {
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      Object.assign(payload, { attachment: data, fileType: file.type });
    } catch {
      showFormError('This attachment could not be read.');
      return;
    }
  }
  if (screen === 'six') {
    document.activeElement?.blur();
    void saveDomain('/api/six', 'POST', payload, 'Request queued.');
  }
});

app.addEventListener('change', event => {
  if (event.target.id === 'inventory-location') {
    inventoryLocation = event.target.value;
    void loadData();
  }
});

app.addEventListener('click', event => {
  const actions = event.target.closest('button')?.dataset;
  if (!actions || screen !== 'inventory' && screen !== 'inventory-form') return;
  if (actions.inventoryEdit) {
    const item = inventoryData.items.find(entry => entry.id === actions.inventoryEdit);
    if (item) openDomainForm('inventory', item);
  }
  if ('inventoryArchive' in actions && domainDraft?.id && window.confirm('Archive this stock item?')) {
    void saveDomain(`/api/inventory/${encodeURIComponent(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Stock item archived.', 'inventory');
  }
});

app.addEventListener('submit', event => {
  const form = event.target;
  if (form.id !== 'inventory-form' && !form.dataset.stockItem) return;
  event.preventDefault();
  const fields = Object.fromEntries(new FormData(form));
  if (form.dataset.stockItem) {
    const item = inventoryData.items.find(entry => entry.id === form.dataset.stockItem);
    if (item) {
      document.activeElement?.blur();
      void saveDomain(`/api/inventory/${encodeURIComponent(item.id)}/stock`, 'POST',
        { ...fields, expectedVersion: item.version }, 'Stock updated.');
    }
    return;
  }
  const path = domainDraft?.id ? `/api/inventory/${encodeURIComponent(domainDraft.id)}` : '/api/inventory';
  if (inventoryLocation) inventoryLocation = fields.location;
  void saveDomain(path, domainDraft?.id ? 'PUT' : 'POST',
    { ...fields, expectedVersion: domainDraft?.version }, 'Stock item saved.', 'inventory');
});

function currencyToCents(value) {
  const text = String(value || '0').trim();
  if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(text)) throw Error('Enter a cost with up to two decimal places.');
  const [whole, fraction = ''] = text.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}
function optionalInteger(value) { return value === '' ? null : Number(value); }

app.addEventListener('submit', event => {
  const form = event.target;
  if (!['maintenance-form','maintenance-complete-form','vehicle-form','vehicle-service-form'].includes(form.id)) return;
  event.preventDefault();
  try {
    const source = Object.fromEntries(new FormData(form));
    if (form.id === 'maintenance-form') {
      const id = form.dataset.recordId;
      const fields = { ...source, intervalCount: Number(source.intervalCount), estimatedCostCents: currencyToCents(source.estimatedCost), expectedVersion: id ? Number(form.dataset.version) : undefined };
      delete fields.estimatedCost;
      void saveDomain(id ? `/api/maintenance/${encodeURIComponent(id)}` : '/api/maintenance', id ? 'PUT' : 'POST', fields, 'Maintenance schedule saved.', 'maintenance');
    } else if (form.id === 'maintenance-complete-form') {
      const id = form.dataset.recordId;
      void saveDomain(`/api/maintenance/${encodeURIComponent(id)}/complete`, 'POST', {
        expectedVersion: Number(form.dataset.version), performedOn: source.performedOn,
        costCents: currencyToCents(source.cost), notes: source.notes,
      }, 'Maintenance completion saved.', 'maintenance');
    } else if (form.id === 'vehicle-form') {
      const id = form.dataset.recordId;
      const fields = { ...source, year: Number(source.year), odometer: Number(source.odometer), expectedVersion: id ? Number(form.dataset.version) : undefined };
      void saveDomain(id ? `/api/vehicles/${encodeURIComponent(id)}` : '/api/vehicles', id ? 'PUT' : 'POST', fields, 'Vehicle profile saved.', 'vehicles');
    } else {
      void saveDomain('/api/vehicles/services', 'POST', {
        vehicleId: form.dataset.vehicleId, serviceType: source.serviceType, performedOn: source.performedOn,
        odometer: Number(source.odometer), dueOn: source.dueOn || null,
        dueOdometer: optionalInteger(source.dueOdometer), intervalMonths: optionalInteger(source.intervalMonths),
        intervalMiles: optionalInteger(source.intervalMiles), costCents: currencyToCents(source.cost), notes: source.notes,
      }, 'Vehicle service saved.', 'vehicles');
    }
  } catch (err) {
    showFormError(err.message || 'Check the form and try again.');
  }
});

app.addEventListener('click', event => {
  const actions = event.target.closest('button')?.dataset;
  if (!actions || !me) return;
  if ('wallFullscreen' in actions) {
    if (document.fullscreenElement) void document.exitFullscreen?.().catch(() => {});
    else void app.requestFullscreen?.().catch(() => {});
  }
  if ('announcementExpired' in actions) {
    showExpired = !showExpired;
    void loadData();
  }
  if (actions.announcementEdit) {
    const item = announcementData.items.find(entry => entry.id === actions.announcementEdit);
    if (item) openDomainForm('announcement', item);
  }
  if (actions.announcementAck) {
    const item = announcementData.items.find(entry => entry.id === actions.announcementAck);
    if (item) void saveDomain(`/api/announcements/${encodeURIComponent(item.id)}/ack`, 'POST',
      { expectedVersion: item.version }, 'Announcement acknowledged.');
  }
  if ('announcementArchive' in actions && domainDraft && window.confirm('Archive this announcement?')) {
    void saveDomain(`/api/announcements/${encodeURIComponent(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Announcement archived.', 'announcements');
  }
});
app.addEventListener('submit', event => {
  const form = event.target;
  if (form.id !== 'announcement-form') return;
  event.preventDefault();
  const source = new FormData(form);
  const path = domainDraft ? `/api/announcements/${encodeURIComponent(domainDraft.id)}` : '/api/announcements';
  void saveDomain(path, domainDraft ? 'PUT' : 'POST', { ...Object.fromEntries(source),
    pinned: source.has('pinned'), expectedVersion: domainDraft?.version }, 'Announcement published.', 'announcements');
});

setInterval(() => {
  if (screen === 'wall' && me) {
    if (!navigator.onLine) render();
    else void loadData();
  }
}, 30_000);

app.addEventListener('click', event => {
  const control = event.target.closest('button[data-habit-check],button[data-habit-edit],button[data-habit-archive]');
  if (!control || !me) return;
  const actions = control.dataset;
  if ('habitArchive' in actions && domainDraft?.id && window.confirm('Archive this habit?')) {
    void saveDomain(`/api/habits/${encodeURIComponent(domainDraft.id)}`, 'DELETE',
      { expectedVersion: domainDraft.version }, 'Habit archived.', 'habits');
    return;
  }
  const selected = habitsData?.habits.find(item => item.id === (actions.habitCheck || actions.habitEdit));
  if (!selected) return;
  if (actions.habitEdit) openDomainForm('habit', selected);
  else void saveDomain(`/api/habits/${encodeURIComponent(selected.id)}/check`, 'POST',
    { expectedVersion: selected.version, date: habitsData.date }, 'Habit checked in.');
});

app.addEventListener('submit', event => {
  const form = event.target;
  if (!['habit-form','allowance-form'].includes(form.id)) return;
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  if (form.id === 'allowance-form') {
    const wallet = allowanceData?.wallets.find(entry => entry.id === data.memberId);
    if (!wallet) return;
    document.activeElement?.blur();
    void saveDomain('/api/allowance', 'POST', { ...data, expectedVersion: wallet.version }, 'Allowance recorded.');
    return;
  }
  const id = domainDraft?.id;
  void saveDomain(id ? `/api/habits/${encodeURIComponent(id)}` : '/api/habits', id ? 'PUT' : 'POST',
    { ...data, memberId: domainDraft?.member_id || data.memberId || me.id, expectedVersion: domainDraft?.version },
    'Habit saved.', 'habits');
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
    document.activeElement?.blur();
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

function flushQueue() {
  if (queueReplay || !me || !navigator.onLine) return queueReplay;
  queueReplay = replayCompletions(me.id).catch(() => {}).finally(() => { queueReplay = null; });
  return queueReplay;
}

async function replayCompletions(memberId) {
  const queue = (await queuedFor(memberId)).filter(operation => operation.nextAt <= Date.now());
  if (!queue.length || me?.id !== memberId) return;
  let session;
  try {
    const response = await api('/api/me');
    if (response.status === 401) return expireLocalSession();
    if (!response.ok) return;
    session = await response.json();
  } catch {
    return;
  }
  if (me?.id !== memberId) return;
  if (session.user?.id !== memberId) return expireLocalSession();
  csrf = session.csrf;
  let refreshed = false;
  for (const operation of queue) {
    if (me?.id !== memberId) return;
    try {
      const response = await api(`/api/items/${encodeURIComponent(operation.itemId)}/complete`, {
        method: 'POST',
        body: JSON.stringify({ csrf: session.csrf, memberId, expectedVersion: operation.expectedVersion,
          mutationId: operation.mutationId }),
      });
      if (me?.id !== memberId) return;
      if (response.status === 401) return expireLocalSession();
      if (response.status >= 500) throw Error('Temporary server error');
      await removeQueued(operation.key);
      refreshed = true;
      if (!response.ok) {
        const detail = await response.json();
        setNotice(detail.error || 'A queued completion could not be saved.', true);
      }
    } catch {
      operation.attempt++;
      if (operation.attempt >= 3) {
        await removeQueued(operation.key);
        refreshed = true;
        setNotice('A completion could not sync. Refresh and try again.', true);
      } else {
        const delay = 1000 * (2 ** operation.attempt);
        operation.nextAt = Date.now() + delay;
        await storeQueued(operation);
        setTimeout(flushQueue, delay);
      }
    }
  }
  if (refreshed && me?.id === memberId) await loadData();
}
async function complete(id){const sources=screen==='shopping'?(shoppingData?.items||[]):screen==='today'?
  [...(dashboardData?.chores||[]),...(dashboardData?.overdue||[]),...(dashboardData?.unscheduled||[])]:items;
  const item=sources.find(i=>i.id===id);if(!item)return;const original=item.completed,operation={key:`${me.id}:${crypto.randomUUID()}`,userId:me.id,itemId:item.id,expectedVersion:item.version,mutationId:crypto.randomUUID(),attempt:0,nextAt:0};item.completed=1;render();let response;try{response=await api(`/api/items/${encodeURIComponent(id)}/complete`,{method:'POST',body:JSON.stringify({csrf,expectedVersion:operation.expectedVersion,mutationId:operation.mutationId,memberId:operation.userId})})}catch{try{await storeQueued(operation)}catch{item.completed=original;setNotice('This device could not queue the change. Reconnect and try again.',true);return}offline=true;authState='offline-authorized';if(navigator.onLine)setTimeout(flushQueue,1000);setNotice('Completion is queued for this signed-in member. It will sync after reconnection.');return}if(response.status===401){item.completed=original;await expireLocalSession();return}if(response.status===403){item.completed=original;setNotice('This account is not allowed to complete that task.',true);return}if(response.status===404){items=items.filter(x=>x.id!==id);setNotice('That task no longer exists. The list has been refreshed.');render();return}if(response.status===409){item.completed=original;setNotice('This task changed on another device. Refreshing the household list.');await loadData();return}if(response.status===422){item.completed=original;const data=await response.json();setNotice(data.error||'Refresh this task before completing it.',true);render();return}if(response.status>=500){try{await storeQueued(operation)}catch{item.completed=original;setNotice('This device could not queue a retry. Please try again.',true);return}setTimeout(flushQueue,1000);setNotice('The server is temporarily unavailable. This completion will retry.');return}if(!response.ok){item.completed=original;setNotice('The task could not be completed.',true);return}const saved=await response.json();Object.assign(item,saved);offline=false;authState='authenticated';render()}
const itemRequests = new WeakMap();

async function submitItem(form) {
  const fields = new FormData(form);
  const kind = screen.slice(4);
  const payload = {
    kind, title: fields.get('title'), details: fields.get('details'), dueAt: fields.get('dueAt'),
    assignedTo: fields.get('assignedTo'), points: Number(fields.get('points') || 0),
  };
  const fingerprint = JSON.stringify(payload);
  let mutation = itemRequests.get(form);
  if (!mutation || mutation.fingerprint !== fingerprint) {
    mutation = { fingerprint, id: crypto.randomUUID() };
    itemRequests.set(form, mutation);
  }
  const previous = screen;
  const actor = me?.id;
  try {
    const response = await api('/api/items', { method: 'POST', body: JSON.stringify({ ...payload, csrf, mutationId: mutation.id }) });
    if (previous !== screen || actor !== me?.id) return;
    if (response.status === 401) return expireLocalSession();
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    screen = kind === 'task' ? 'tasks' : 'more';
    message = 'Saved to your household.';
    error = '';
    await loadData();
  } catch (err) {
    if (previous === screen && actor === me?.id) showFormError(err instanceof TypeError ? 'Reconnect to save this record.' : err.message);
  }
}
app.addEventListener('click',async e=>{const nav=e.target.closest('[data-nav]'),act=e.target.closest('[data-action]'),check=e.target.closest('[data-complete]'),newKind=e.target.closest('[data-new-kind]');if(nav){if(screen==='wall'&&document.fullscreenElement)void document.exitFullscreen?.().catch(()=>{});quickOpen=false;screen=nav.dataset.nav;message='';error='';if(screen==='more'||screen==='settings')render();await loadData();return}if(newKind?.dataset.newKind==='meal'){void openMeal();return}if(['chore','reward','recipe','inventory','announcement'].includes(newKind?.dataset.newKind)){openDomainForm(newKind.dataset.newKind);return}if(newKind?.dataset.newKind==='event'){quickOpen=false;openCalendarForm();return}if(newKind?.dataset.newKind==='shopping'){quickOpen=false;screen='shopping';await loadData();return}if(newKind){quickOpen=false;screen=`new:${newKind.dataset.newKind}`;message='';render();return}if(check){await complete(check.dataset.complete);return}if(act?.dataset.action==='add'){quickOpen=!quickOpen;render();return}if(act?.dataset.action==='logout'){const leavingId=me.id;localStorage.setItem(SIGNED_OUT,'1');try{await api('/api/logout',{method:'POST',body:JSON.stringify({csrf})})}catch{}if(live){live.close();live=null}try{await clearQueued(leavingId)}catch{}clearLegacyCaches();resetPrivateViews();me=null;csrf='';members=[];items=[];offline=false;authState='signed-out';screen='today';render();return}if(act?.dataset.action==='theme'){const cur=document.documentElement.dataset.theme||'system',next=cur==='system'?'light':cur==='light'?'dark':'system';applyTheme(next);return}});

app.addEventListener('click', event => {
  const action = event.target.closest('button')?.dataset;
  if (!action || !me) return;
  if (action.propertyOpen === 'maintenance') return openDomainForm('maintenance');
  if (action.propertyOpen === 'vehicle') return openDomainForm('vehicle');
  if (action.maintTemplate) return openDomainForm('maintenance', { templateTitle: action.maintTemplate });
  if (screen === 'maintenance' || screen === 'maintenance-form' || screen === 'maintenance-complete-form') {
    if (action.maintEdit) {
      const item = propertyCareData?.schedules.find(row => row.id === action.maintEdit);
      if (item) openDomainForm('maintenance', item);
    }
    if (action.maintComplete) {
      const item = propertyCareData?.schedules.find(row => row.id === action.maintComplete);
      if (item) openDomainForm('maintenance-complete', item);
    }
    if (action.maintArchive) {
      const item = propertyCareData?.schedules.find(row => row.id === action.maintArchive);
      if (item && window.confirm(`Archive ${item.title}? Its completion history will be kept.`))
        void saveDomain(`/api/maintenance/${encodeURIComponent(item.id)}`, 'DELETE', { expectedVersion: item.version }, 'Maintenance schedule archived.', 'maintenance');
    }
  }
  if (screen === 'vehicles' || screen === 'vehicle-form' || screen === 'vehicle-service-form') {
    if (action.vehicleEdit) {
      const item = propertyCareData?.vehicles.find(row => row.id === action.vehicleEdit);
      if (item) openDomainForm('vehicle', item);
    }
    if (action.serviceNew) {
      const vehicle = propertyCareData?.vehicles.find(row => row.id === action.serviceNew);
      if (vehicle) openDomainForm('vehicle-service', { vehicle });
    }
  }
});
app.addEventListener('submit',async e=>{const form=e.target;if(form.id==='item-form'){e.preventDefault();await submitItem(form);return}if(form.id==='member-form'){e.preventDefault();try{const payload=Object.fromEntries(new FormData(form));payload.csrf=csrf;const r=await api('/api/members',{method:'POST',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);message='Member added.';await loadData()}catch(err){error=err.message;render()}return}if(form.dataset.profileId){e.preventDefault();document.activeElement?.blur();try{const payload={...Object.fromEntries(new FormData(form)),targetId:form.dataset.profileId,csrf};const r=await api('/api/members/profile',{method:'PUT',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);if(d.id===me.id)Object.assign(me,{displayName:d.displayName,color:d.color,avatar:d.avatar});message='Profile saved.';await loadData()}catch(err){error=err.message;render()}return}if(form.dataset.memberReset){e.preventDefault();document.activeElement?.blur();try{const payload={...Object.fromEntries(new FormData(form)),targetId:form.dataset.memberReset,csrf};const r=await api('/api/members/password/reset',{method:'POST',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);message='Password reset. Active sessions were revoked.';await loadData()}catch(err){error=err.message;render()}return}if(form.id==='password-form'){e.preventDefault();document.activeElement?.blur();try{const payload=Object.fromEntries(new FormData(form));payload.csrf=csrf;const r=await api('/api/password',{method:'POST',body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.error);message='Password updated. Other sessions were signed out.';await loadData()}catch(err){error=err.message;render()}}});
app.addEventListener('click',async e=>{const status=e.target.closest('[data-account-status]'),revoke=e.target.closest('[data-session-revoke]');if(status){const disabled=status.dataset.active==='true';if(disabled&&!window.confirm('Disable this account and sign out its active devices?'))return;try{const r=await api('/api/members/status',{method:'POST',body:JSON.stringify({csrf,targetId:status.dataset.accountStatus,disabled})}),d=await r.json();if(!r.ok)throw Error(d.error);message=disabled?'Account disabled.':'Account reactivated.';await loadData()}catch(err){error=err.message;render()}return}if(revoke){if(!window.confirm('Revoke this device session?'))return;try{const r=await api('/api/sessions/revoke',{method:'POST',body:JSON.stringify({csrf,deviceId:revoke.dataset.sessionRevoke})}),d=await r.json();if(!r.ok)throw Error(d.error);if(d.current){await expireLocalSession();return}message='Device session revoked.';await loadData()}catch(err){error=err.message;render()}}});
app.addEventListener('click', async event => {
  const control = event.target.closest('[data-member-sessions]');
  if (!control) return;
  try {
    const response = await api('/api/sessions/list', { method: 'POST',
      body: JSON.stringify({ csrf, targetId: control.dataset.memberSessions }) });
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Sessions could not be loaded.');
    memberSessionsData = { ...memberSessionsData, [control.dataset.memberSessions]: data.sessions };
    render();
  } catch (err) {
    error = err.message || 'Sessions could not be loaded.';
    render();
  }
});
function applyTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('hs-theme',theme);document.documentElement.style.colorScheme=theme==='system'?'light dark':theme}const savedTheme=localStorage.getItem('hs-theme')||'system';applyTheme(savedTheme);app.addEventListener('change',e=>{if(e.target.id==='theme-select')applyTheme(e.target.value)});
let sessionCheck=null;
async function revalidateSession(){if(sessionCheck)return sessionCheck;sessionCheck=(async()=>{try{const response=await api('/api/me');if(response.status===401){await expireLocalSession();return}if(!response.ok)return;const data=await response.json();if(!data.user||data.user.id!==me?.id){await expireLocalSession();return}csrf=data.csrf;offline=false;authState='authenticated'}catch{if(me){offline=true;authState='offline-authorized'}if(!formHasDraft())render()}})();try{await sessionCheck}finally{sessionCheck=null}}
app.addEventListener('pointerdown', () => { latestInteraction = performance.now(); }, { capture: true });
app.addEventListener('keydown', () => { latestInteraction = performance.now(); }, { capture: true });

function scheduleLiveRefresh() {
  if (refreshTimer) return;
  refreshTimer = setTimeout(() => {
    refreshTimer = null;
    if (!me) return;
    if (performance.now() - latestInteraction < 350) {
      scheduleLiveRefresh();
      return;
    }
    void loadData({ background: true });
  }, 400);
}

function startLive() {
  if (!me || !navigator.onLine || !window.EventSource || live && live.readyState !== 2) return;
  live = new EventSource('/api/events');
  live.addEventListener('open', scheduleLiveRefresh);
  live.addEventListener('household-change', scheduleLiveRefresh);
  live.addEventListener('error', revalidateSession);
}

window.addEventListener('storage', event => {
  if (event.key === SIGNED_OUT && event.newValue === '1' && me) void expireLocalSession();
});
window.addEventListener('online',()=>{startLive();flushQueue()});window.addEventListener('offline',()=>{offline=!!me;if(me)authState='offline-authorized';if(!formHasDraft())render()});if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
(async()=>{try{const state=await fetch('/api/setup-state').then(r=>r.json());if(!state.initialized){renderAuth(true);return}if(localStorage.getItem(SIGNED_OUT)==='1'){renderAuth(false);return}const r=await api('/api/me');if(!r.ok)throw Error();const d=await r.json();if(d.user){me=d.user;csrf=d.csrf;authState='authenticated';if(me.role==='display')screen='wall';await loadData();startLive()}else{authState='signed-out';renderAuth(false)}}catch{me=null;members=[];items=[];offline=false;authState='signed-out';error='Household server is unavailable. Connect to your local network and sign in to continue.';renderAuth(false)}})();

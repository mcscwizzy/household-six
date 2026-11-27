import { formatDay, shiftDay } from './dates.js';
import { escapeHtml as h } from './html.js';

const SLOTS = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snack: 'Snacks' };

export function mealView(data, canEdit, shoppingList) {
  if (!data) return '<h1>Meal plan</h1><p>Connect to load this week’s meal plan.</p>';
  const label = day => formatDay(day, { month: 'short', day: 'numeric' });
  const days = [];
  const renderMeal = item => `<div class="meal-entry"><div><strong>${h(item.title)}</strong>
    ${item.servings ? `<div class="item-detail">${item.servings} servings</div>` : ''}
    ${item.details ? `<div class="item-detail">${h(item.details)}</div>` : ''}</div>
    ${canEdit ? `<button class="text-button" data-meal-edit="${h(item.id)}" aria-label="Edit meal ${h(item.title)}">Edit</button>` : ''}</div>`;
  for (let day = data.weekStart; day < data.weekEnd; day = shiftDay(day, 1)) {
    days.push(`<section class="card meal-day"><h3>${formatDay(day, { weekday: 'long', month: 'short', day: 'numeric' })}</h3>
    ${Object.entries(SLOTS).map(([slot, name]) => {
      const entries = data.meals.filter(item => item.day === day && item.slot === slot);
      return `<div class="meal-slot"><h4>${name}</h4>${entries.map(renderMeal).join('')}
      ${canEdit ? `<button class="text-button" data-meal-date="${h(day)}" data-meal-slot="${slot}"
        aria-label="Plan ${name.toLowerCase()} on ${label(day)}">＋ Plan</button>` : entries.length ? '' : '<span class="item-detail">Unplanned</span>'}</div>`;
    }).join('')}</section>`);
  }
  const unscheduled = data.meals.filter(item => !item.day);
  return `<header class="greeting"><h1>Meal plan</h1><button class="secondary" data-nav="recipes">Recipes</button></header>
    <div class="calendar-controls calendar-navigation">
      <h2>${label(data.weekStart)} – ${label(shiftDay(data.weekEnd, -1))}</h2>
      <div class="actions">
        <button class="secondary" data-meal-step="-7" aria-label="Previous meal week">‹</button>
        <button class="secondary" data-meal-step="0">This week</button>
        <button class="secondary" data-meal-step="7" aria-label="Next meal week">›</button>
      </div>
    </div>
    ${canEdit ? `<form id="grocery-sync-form" class="card shopping-toolbar">
      <label class="field">Shopping list<select name="listId">${data.lists.map(list => `<option value="${h(list.id)}" ${list.id === shoppingList ? 'selected' : ''}>${h(list.name)}</option>`).join('')}</select></label>
      <button class="primary">Sync groceries for this week</button>
    </form>` : ''}
    <div class="meal-week">${days.join('')}</div>
    ${unscheduled.length ? `<section class="card meal-day"><h3>Unscheduled meals</h3>${unscheduled.map(renderMeal).join('')}</section>` : ''}`;
}

export function mealForm(draft, recipes, fallbackDay) {
  return `<header class="greeting"><h1>${draft?.id ? 'Edit planned meal' : 'Plan a meal'}</h1></header>
  <form id="meal-form" class="card form form-card">
    <label class="field">Date<input type="date" name="date" value="${h(draft?.day || fallbackDay)}" required></label>
    <label class="field">Meal<select name="slot">${Object.entries(SLOTS).map(([slot, label]) =>
      `<option value="${slot}" ${(draft?.slot || 'dinner') === slot ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
    <label class="field">Recipe<select name="recipeId"><option value="">Choose a recipe or enter a name</option>
      ${draft?.recipe_id && !recipes.some(item => item.id === draft.recipe_id)
        ? `<option value="${h(draft.recipe_id)}" selected>${h(draft.recipe_title)} (archived)</option>` : ''}
      ${recipes.filter(item => item.servings).map(item => `<option value="${h(item.id)}" data-servings="${item.servings}"
        ${draft?.recipe_id === item.id ? 'selected' : ''}>${h(item.title)}</option>`).join('')}</select></label>
    <label class="field">Meal name<input name="title" value="${h(draft?.id ? draft.title : '')}" maxlength="120"></label>
    <label class="field">Servings<input name="servings" type="number" min="1" max="1000" value="${draft?.servings || 4}" required></label>
    <label class="field">Notes<textarea name="details" maxlength="1000">${h(draft?.details)}</textarea></label>
    <div class="actions">
      <button class="primary">Save meal</button>
      <button type="button" class="secondary" data-nav="meals">Cancel</button>
      ${draft?.id ? '<button type="button" class="secondary danger" data-meal-archive>Remove meal</button>' : ''}
    </div>
  </form>`;
}

export function recipesView(recipes, canEdit) {
  return `<header class="greeting"><h1>Recipes</h1>${canEdit ? '<button class="primary" data-domain-open="recipe">New recipe</button>' : ''}</header>
    <div class="list">${recipes?.length ? recipes.map(recipe => `<details class="card domain-details recipe-card" data-panel="recipe-${h(recipe.id)}">
      <summary>${h(recipe.title)}${recipe.servings ? ` · ${recipe.servings} servings` : ''}</summary>
      ${recipe.details ? `<p>${h(recipe.details)}</p>` : ''}
      ${recipe.servings ? `<div class="recipe-scale"><label class="field">Scale to servings
        <input type="number" min="1" max="1000" value="${recipe.servings}" data-recipe-scale="${recipe.servings}">
      </label></div><ul class="recipe-ingredients">${recipe.ingredients.map(item => `<li>
        <span data-base-quantity="${h(item.quantity)}">${h(item.quantity)}</span>
        ${h(item.unit)} ${h(item.name)}</li>`).join('')}</ul>` : ''}
      ${recipe.instructions ? `<p class="recipe-instructions">${h(recipe.instructions)}</p>` : ''}
      ${canEdit ? `<div class="actions">
        <button class="secondary" data-recipe-edit="${h(recipe.id)}" aria-label="Edit recipe ${h(recipe.title)}">Edit</button>
        ${recipe.servings ? `<button class="primary" data-recipe-plan="${h(recipe.id)}">Plan this recipe</button>` : ''}
      </div>` : ''}
    </details>`).join('') : '<p class="empty">No recipes saved yet.</p>'}</div>`;
}

export function ingredientFields(item = {}) {
  return `<div class="ingredient-fields">
    <label class="field">Ingredient<input name="name" value="${h(item.name)}" maxlength="120" required></label>
    <label class="field">Ingredient quantity<input name="quantity" type="number" inputmode="decimal" min="0.0001" max="999999.9999" step="0.0001" value="${h(item.quantity)}" required></label>
    <label class="field">Unit<input name="unit" value="${h(item.unit)}" maxlength="30" placeholder="cups"></label>
    <label class="field">Shopping category<input name="category" value="${h(item.category)}" maxlength="60" placeholder="Pantry"></label>
    <button class="text-button" data-ingredient-remove type="button">Remove ingredient</button>
  </div>`;
}

export function recipeForm(draft) {
  const ingredients = draft?.ingredients?.length ? draft.ingredients : [{}];
  return `<header class="greeting"><h1>${draft ? 'Edit recipe' : 'New recipe'}</h1></header>
    <form id="recipe-form" class="card form">
      <label class="field">Recipe name<input name="title" value="${h(draft?.title)}" maxlength="120" required></label>
      <label class="field">Notes<textarea name="details" maxlength="1000">${h(draft?.details)}</textarea></label>
      <label class="field">Recipe servings<input name="servings" type="number" min="1" max="1000" value="${draft?.servings || 4}" required></label>
      <fieldset class="domain-fieldset"><legend>Ingredients</legend>
        <div id="ingredient-list">${ingredients.map(ingredientFields).join('')}</div>
        <button class="secondary" type="button" data-ingredient-add>Add ingredient</button>
      </fieldset>
      <label class="field">Instructions<textarea name="instructions" maxlength="8000">${h(draft?.instructions)}</textarea></label>
      <div class="actions">
        <button class="primary">Save recipe</button>
        <button class="secondary" data-nav="recipes" type="button">Cancel</button>
        ${draft ? '<button class="secondary danger" data-recipe-archive type="button">Archive recipe</button>' : ''}
      </div>
    </form>`;
}

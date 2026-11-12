'use strict';
/* Тексты дела */
const legendMarkdown = `## Дело № 001. Загадка исчезнувшего релиза

Сегодня утром команда Artcode готовила релиз версии 2.8.0.

Работа шла по плану: разработчик подготовил сборку, тестировщик проверил её, аналитик оформил заметки к релизу.

Но в 10:21 релизная карточка исчезла с рабочей доски.

Никто не признаётся, что удалял её. При этом в системе остались сообщения сотрудников, журналы автоматизации и записи о статусах задач.

Все участники процесса уверены, что выполнили свою часть работы.

Что произошло на самом деле? Релиз действительно выпустили, кто-то удалил карточку или система самостоятельно скрыла её?

Ваша задача — изучить материалы дела, восстановить последовательность событий и установить, что произошло с релизом 2.8.0.

**Дело открыто. У вас есть 15 минут.**

---

`;

const materialsMarkdown = `## УЛИКА № 1. КАРТОЧКА РЕЛИЗА

**Тип материала:** интерфейс трекера задач.

**Карточка:** REL-280  
**Название:** Release 2.8.0  
**Создана:** 09:40  
**Снимок карточки:** 10:19:30  
**Текущий статус:** In Progress

**Связанные задачи:**

| ID | Название | Ответственный | Статус |
|---|---|---|---|
| DEV-280 | Подготовить сборку | Макс Кодиков | Done |
| QA-280 | Проверить сборку | Кот Котовый | Done |
| BA-280 | Подготовить заметки к релизу | Алиса Текстова | Done |

**Дополнительная информация:**

- Отдельная задача Production Deployment в карточке отсутствует.
- В карточке нет обязательного условия подтверждения успешного развёртывания в Production.
- Карточка находится в статусе In Progress на момент снимка — 10:19:30.

---

## УЛИКА № 2. СООБЩЕНИЕ РАЗРАБОТЧИКА

**Тип материала:** корпоративный чат.

**Канал:** #release-2-8-0

**10:02 — @max.dev (Макс Кодиков)**

> Сборка 2.8.0 готова. Pipeline прошёл без ошибок, артефакт создан. Передал на QA.

**Прикреплённая карточка CI/CD:**

**Pipeline:** PIPE-280  
**Version:** 2.8.0  
**Commit:** 7F2A  
**Environment:** CI

| Параметр | Значение |
|---|---|
| Build | PASSED |
| Artifact | CREATED |
| Deployment | NOT STARTED |
| Task DEV-280 | DONE |

**Время завершения задачи DEV-280:** 10:02:04

---

## УЛИКА № 3. ОТЧЁТ ТЕСТИРОВЩИКА

**Тип материала:** интерфейс QA-системы и сообщение в чате.

**Канал:** #release-2-8-0

**10:14 — @kot.kotovyi (Кот Котовый)**

> Проверку завершил. Критичных проблем не обнаружено, сборка прошла QA. Можно передавать дальше.

**Прикреплённый QA-отчёт:**

**Report ID:** QA-280  
**Build:** ART-280  
**Version:** 2.8.0  
**Environment:** STAGING

| Параметр | Значение |
|---|---|
| Test result | PASSED |
| Critical issues | 0 |
| Production verification | NOT PERFORMED |
| Task QA-280 | DONE |

**Время завершения задачи QA-280:** 10:14:12

---

## УЛИКА № 4. СООБЩЕНИЕ АНАЛИТИКА

**Тип материала:** корпоративный чат и карточка документа.

**Канал:** #release-2-8-0

**10:19 — @alice.ba (Алиса Текстова)**

> Заметки к релизу готовы, всё проверила и оформила. Добавила описание изменений.

**Прикреплённый документ:**

**Document ID:** RN-280  
**Название:** Release Notes 2.8.0

| Параметр | Значение |
|---|---|
| Document status | READY |
| Document publication status | NOT PUBLISHED |
| Task BA-280 | DONE |

**Время завершения задачи BA-280:** 10:19:08

---

## УЛИКА № 5. ПЕРЕПИСКА О ВЫПУСКЕ

**Тип материала:** корпоративный чат.

**Канал:** #release-2-8-0

**10:16 — @vera.deploy (Вера Деплой)**

> Production пока не трогаем. Окно развёртывания запланировано на 11:00. Жду подтверждения согласования.

**10:17 — @max.dev (Макс Кодиков)**

> Понял, со своей стороны всё готово. Сборка и артефакт на месте.

**10:20:03 — @release.bot (ReleaseBot)**

> Все связанные задачи REL-280 завершены. Статус родительской карточки изменён на Completed.

---

## УЛИКА № 6. ЖУРНАЛ АВТОМАТИЗАЦИИ

**Тип материала:** системный лог.

**Rule ID:** AUTO-REL-04  
**Rule name:** Complete parent when all linked tasks are done  
**Target card:** REL-280  
**Execution ID:** AUTO-280-102001  
**Result:** SUCCESS  
**Executed by:** ReleaseBot

**Условие запуска:**

> All linked tasks status = Done

**Действие:**

> Change parent card status to Completed

**Журнал событий:**

| Время | Событие |
|---|---|
| 10:02:04 | DEV-280 status changed to Done |
| 10:14:12 | QA-280 status changed to Done |
| 10:19:08 | BA-280 status changed to Done |
| 10:20:01 | AUTO-REL-04 triggered |
| 10:20:02 | REL-280 status changed: In Progress → Completed |

**Результат выполнения правила:**

- Previous status: In Progress
- New status: Completed
- Target: REL-280
- Trigger: all linked tasks completed
- Deployment verification required: NO
- Production deployment status checked: NO
- Release Engineer approval checked: NO

---

## УЛИКА № 7. ИСЧЕЗНОВЕНИЕ КАРТОЧКИ С РАБОЧЕЙ ДОСКИ

**Тип материала:** интерфейс рабочей доски и журнал событий.

**Доска:** Product Release Board

**Настройки фильтра на момент обновления:**

| Параметр | Значение |
|---|---|
| Show only active tasks | ON |
| Hide completed tasks | ON |

**Журнал событий:**

| Время | Событие |
|---|---|
| 10:20:02 | REL-280 status changed to Completed |
| 10:21:00 | Board refreshed |
| 10:21:01 | Active tasks filter applied |
| 10:21:01 | REL-280 hidden from current view |

**Результат проверки карточки:**

- Card record exists: YES
- Current status: Completed
- Card deleted: NO
- Card archived: NO
- Delete event: NOT FOUND
- Archive event: NOT FOUND
- Audit log: COMPLETE

---

## УЛИКА № 8. ИСТОРИЯ РАЗВЁРТЫВАНИЙ PRODUCTION

**Тип материала:** интерфейс CI/CD — история развёртываний.

**Project:** Product Release  
**Environment:** Production  
**Snapshot time:** 10:21:30  
**Audit period:** 09:00–10:21  
**Audit status:** COMPLETE

**Фильтр:** Release reference = REL-280

**Результат поиска:**

| Параметр | Значение |
|---|---|
| Release reference | REL-280 |
| Deployment records matching REL-280 | 0 |
| Deployment job | NOT FOUND |
| Production artifact | NOT FOUND |
| Deployment confirmation | NOT FOUND |

**Последнее успешное развёртывание в Production:**

| Параметр | Значение |
|---|---|
| Version | 2.7.4 |
| Environment | Production |
| Result | SUCCESS |
| Deployment time | 09:12 |

**Текущая версия в Production на 10:21:30:** 2.7.4

**Ограничение вывода:** материалы подтверждают состояние системы на момент 10:21. Они не позволяют утверждать, что релиз не мог быть развёрнут позднее.

---

## ЛОЖНЫЙ СЛЕД № 1. ЗЕЛЁНАЯ ПАНЕЛЬ МОНИТОРИНГА

**Тип материала:** дашборд мониторинга.

**Dashboard:** Production Health  
**Время снимка:** 10:21

| Показатель | Значение |
|---|---|
| Availability | 100% |
| Error rate | 0.1% |
| Response time | Normal |
| System status | HEALTHY |
| Current production version | 2.7.4 |

**Сообщение в чате:**

**10:21 — @vera.deploy**

> Мониторинг зелёный, критичных отклонений нет.

---

## ЛОЖНЫЙ СЛЕД № 2. ИСТОРИЯ ПРЕДЫДУЩЕГО РЕЛИЗА

**Тип материала:** архивная карточка релиза и журнал событий.

**Release:** 2.7.0  
**Card ID:** REL-270

**История событий:**

| Время | Событие |
|---|---|
| 14:30:00 | All linked tasks completed |
| 14:30:01 | Automation changed parent status to Completed |
| 14:45:00 | Production Deployment DEP-270 completed successfully |
| 14:46:00 | Deployment verification completed |

**Дополнительная информация:**

- Deployment ID: DEP-270
- Version: 2.7.0
- Environment: Production
- Result: SUCCESS

---

`;

const finaleMarkdown = `## Что произошло на самом деле

Релиз 2.8.0 не был развёрнут в Production к моменту исчезновения карточки с рабочей доски.

Команда выполнила три подготовительные задачи:

1. Разработчик собрал версию 2.8.0 и создал артефакт.
2. Тестировщик проверил сборку в Staging.
3. Аналитик подготовил заметки к релизу.

После завершения всех трёх связанных задач сработало правило автоматизации AUTO-REL-04.

Оно проверяло только одно условие: все связанные задачи должны иметь статус Done.

Условие выполнилось, и в 10:20:02 автоматизация перевела родительскую карточку REL-280 из In Progress в Completed.

При этом правило не проверяло:

- было ли выполнено развёртывание в Production;
- существует ли успешное событие Deployment;
- получено ли согласование Release Engineer;
- завершены ли обязательные условия фактического выпуска.

В 10:21 рабочая доска обновилась. Поскольку был включён фильтр скрытия завершённых задач, карточка REL-280 перестала отображаться.

Карточку никто не удалял и не архивировал. Она продолжала существовать в системе со статусом Completed.

История Production-развёртываний подтверждает, что на момент 10:21:30 версия 2.8.0 не была выпущена. Последняя успешная версия в Production — 2.7.4.

## Единственная подтверждённая последовательность

| Время | Событие | Подтверждение |
|---|---|---|
| 09:40 | Создана карточка релиза REL-280 | Улика № 1 |
| 10:02:04 | Завершена задача разработки DEV-280 | Улики № 2, 6 |
| 10:14:12 | Завершена задача QA-280 | Улики № 3, 6 |
| 10:19:08 | Завершена задача аналитика BA-280 | Улики № 4, 6 |
| 10:20:01 | Запустилась автоматизация AUTO-REL-04 | Улика № 6 |
| 10:20:02 | Карточка REL-280 получила статус Completed | Улики № 5, 6, 7 |
| 10:20:03 | Бот сообщил об изменении статуса | Улика № 5 |
| 10:21:00 | Рабочая доска обновилась | Улика № 7 |
| 10:21:01 | Фильтр скрыл завершённую карточку | Улика № 7 |

## Почему альтернативные версии не подходят

**Версия 1. Карточку удалили.**

Не подтверждается: карточка существует, событие удаления отсутствует, журнал аудита полный.

**Версия 2. Карточку архивировали.**

Не подтверждается: Card archived = NO, событие архивирования не найдено.

**Версия 3. Релиз уже был выпущен.**

Не подтверждается: в истории Production-развёртываний нет записей для REL-280, а текущая версия Production — 2.7.4.

**Версия 4. Успешная сборка означает успешный выпуск.**

Не подтверждается: в CI указано Deployment NOT STARTED.

**Версия 5. QA подтвердил готовность Production.**

Не подтверждается: тестирование выполнялось в Staging, Production verification не проводилась.

**Версия 6. Зелёный мониторинг подтверждает выпуск 2.8.0.**

Не подтверждается: мониторинг показывает текущую версию 2.7.4.

**Версия 7. Если предыдущий релиз получил статус Completed, значит и этот релиз выпущен.**

Не подтверждается: в истории релиза 2.7.0 есть отдельная запись успешного Production Deployment DEP-270. Для REL-280 аналогичной записи нет.

**Версия 8. Релиз могли развернуть вне родительской карточки.**

Не подтверждается: история развёртываний проверена по идентификатору REL-280. Совпадающих записей нет.

**Версия 9. Релиз могли выпустить после исчезновения карточки.**

Материалы не позволяют исключить такое развитие событий. Однако оно не меняет ответа на главный вопрос: в момент исчезновения карточки релиз 2.8.0 ещё не был развёрнут в Production.

## Главный вывод

**Система отметила завершение подготовки, а не фактический выпуск релиза.**

Карточка исчезла не потому, что релиз удалили или выпустили, а потому, что автоматизация преждевременно перевела её в Completed, после чего фильтр рабочей доски скрыл завершённую карточку.

---

`;

/* Состояние игры */
const KEY = 'artcode-case-001-v1';
const app = document.getElementById('app');
let state = null;

/* Преобразование Markdown */
function esc(value) {
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value ?? '').replace(/[&<>"']/g, char => entities[char]);
}

function inline(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function markdown(raw) {
  const blocks = [];
  let list = null;
  let table = [];

  function closeList() {
    if (list) {
      blocks.push(`</${list}>`);
      list = null;
    }
  }

  function closeTable() {
    if (!table.length) return;
    const rows = table.map((row, index) => {
      const cells = row.map(cell => index
        ? `<td>${inline(cell)}</td>`
        : `<th scope="col">${inline(cell)}</th>`);
      return `<tr>${cells.join('')}</tr>`;
    });
    blocks.push(`<div class="tablewrap"><table>${rows.join('')}</table></div>`);
    table = [];
  }

  for (const line of raw.trim().split(/\r?\n/)) {
    const text = line.trim();
    if (!text || /^---+$/.test(text)) {
      closeList();
      closeTable();
      continue;
    }
    if (/^\|[-:| ]+\|$/.test(text)) continue;
    if (text.startsWith('|')) {
      closeList();
      table.push(text.slice(1, -1).split('|').map(cell => cell.trim()));
      continue;
    }
    closeTable();

    const heading = text.match(/^(#{1,4})\s+(.*)/);
    const item = text.match(/^([-*]|\d+\.)\s+(.*)/);
    if (heading) {
      closeList();
      const level = heading[1].length + 1;
      blocks.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    } else if (item) {
      const type = item[1] === '-' || item[1] === '*' ? 'ul' : 'ol';
      if (list !== type) {
        closeList();
        blocks.push(`<${type}>`);
        list = type;
      }
      blocks.push(`<li>${inline(item[2])}</li>`);
    } else {
      closeList();
      blocks.push(text.startsWith('>')
        ? `<blockquote>${inline(text.slice(1).trim())}</blockquote>`
        : `<p>${inline(text)}</p>`);
    }
  }

  closeList();
  closeTable();
  return blocks.join('');
}

/* Серверная сессия и черновик текущей вкладки. */
const PENDING_KEY = KEY + '-registration-';
const DRAFT_KEY = KEY + '-draft';
const REQUEST_TIMEOUT = 10000;
let busy = false;
let blocked = false;
let finishing = false;
let dirty = false;
let revision = 0;
let pendingMutation = null;
let saveTimer;
let clockBase = 0;
let clockMark = 0;
let lastRefresh = -Infinity;

function defaults() {
  return {
    gameId: 'case-001', sessionId: '', sessionToken: '', teamName: '', status: 'in_progress',
    startedAt: 0, endAt: 0, submittedAt: null, currentScreen: 'start', version: 0, score: null,
    answers: { task1: [], task2: null, task3: [null, null, null, null], task4: [null, null, null, null], task5: null }
  };
}

function message(text) {
  const alert = document.getElementById('saveAlert');
  alert.textContent = text;
  alert.classList.toggle('show', Boolean(text));
}

function save() {
  try {
    if (state.sessionId && state.sessionToken) {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({
        sessionId: state.sessionId, sessionToken: state.sessionToken, answers: state.answers,
        version: state.version, currentScreen: state.currentScreen, dirty, revision, pendingMutation, finishing
      }));
    }
    return true;
  } catch {
    message('Не удалось сохранить данные на устройстве. Не закрывайте страницу до подтверждения сервером.');
    return false;
  }
}

function normalize(answers) {
  return {
    task1: Array.from({ length: 5 }, (_, i) => answers.task1[i] ?? null),
    task2: answers.task2 ?? null,
    task3: Array.from({ length: 4 }, (_, i) => answers.task3[i] ?? null),
    task4: Array.from({ length: 4 }, (_, i) => answers.task4[i] ?? null),
    task5: answers.task5 ?? null
  };
}

function valid(data) {
  if (!data || typeof data.sessionId !== 'string' || typeof data.teamName !== 'string' ||
      !['in_progress', 'submitted', 'timed_out'].includes(data.status) ||
      !Number.isInteger(data.startedAt) || !Number.isInteger(data.endAt) || !Number.isInteger(data.serverNow) ||
      !Number.isInteger(data.version) || !Number.isInteger(data.score) || data.score < 0 || data.score > 20 ||
      !(data.submittedAt === null || Number.isInteger(data.submittedAt)) || !data.answers) return false;
  const answers = data.answers;
  if (!Array.isArray(answers.task1) || answers.task1.length > 5 ||
      !Array.isArray(answers.task3) || answers.task3.length !== 4 ||
      !Array.isArray(answers.task4) || answers.task4.length !== 4) return false;
  const letters = [answers.task2, ...answers.task3, answers.task4[3], answers.task5];
  return answers.task1.every(value => value === null || (Number.isInteger(value) && value >= 1 && value <= 5)) &&
    letters.every(value => value === null || (typeof value === 'string' && /^[А-Я]$/u.test(value))) &&
    answers.task4.slice(0, 3).every(value => value === null || (Number.isInteger(value) && value >= 1 && value <= 10));
}

function apply(data, keepDraft = false) {
  if (!valid(data) || (state.sessionId && data.sessionId !== state.sessionId)) throw Error('invalid response');
  clockBase = data.serverNow;
  clockMark = performance.now();
  const page = state.currentScreen;
  const answers = state.answers;
  Object.assign(state, data);
  state.currentScreen = data.status === 'in_progress'
    ? (page === 'start' ? 'legend' : page)
    : (page === 'debrief' ? 'debrief' : 'result');
  state.answers = keepDraft && data.status === 'in_progress' ? answers : normalize(data.answers);
  if (data.status !== 'in_progress') {
    dirty = false;
    pendingMutation = null;
    finishing = false;
  }
  save();
}

function remaining() {
  return Math.max(0, state.endAt - (clockBase + Math.max(0, performance.now() - clockMark)));
}

function tick() {
  const timer = document.getElementById('timer');
  if (!state.startedAt) { timer.textContent = '15:00 · ожидание'; return; }
  if (state.status !== 'in_progress') { timer.textContent = 'Завершено'; timer.classList.remove('urgent'); return; }
  const ms = remaining();
  const seconds = Math.ceil(ms / 1000);
  timer.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  timer.classList.toggle('urgent', ms <= 60000);
  if (ms <= 0 && !busy && !blocked && performance.now() - lastRefresh >= 2500) refresh();
}

function screen(name) {
  state.currentScreen = name;
  save();
  render();
  window.scrollTo(0, 0);
  app.focus({ preventScroll: true });
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
  try {
    const response = await fetch(path, { cache: 'no-store', ...options, signal: controller.signal });
    let data;
    try { data = await response.json(); } catch { data = null; }
    return { response, data };
  } finally {
    clearTimeout(timeout);
  }
}

function auth() { return { Authorization: 'Bearer ' + state.sessionToken }; }

function unavailable() {
  blocked = true;
  finishing = true;
  clearTimeout(saveTimer);
  for (const [storage, key] of [[localStorage, KEY], [sessionStorage, DRAFT_KEY]]) {
    try {
      const saved = JSON.parse(storage.getItem(key));
      if (saved?.sessionId === state.sessionId) storage.removeItem(key);
    } catch {
      // Недоступное хранилище не должно разблокировать удалённую сессию на текущей странице.
    }
  }
  document.getElementById('timer').classList.remove('urgent');
  message('Сессия недоступна или удалена. Обратитесь к организатору.');
  render();
}

function schedule(delay = 700) {
  clearTimeout(saveTimer);
  if (!blocked && state.status === 'in_progress') saveTimer = setTimeout(flush, delay);
}

function resolveConflict(snapshot, operation) {
  if (!valid(snapshot)) throw Error('invalid response');
  const replay = snapshot.version === operation.version + 1 &&
    JSON.stringify(normalize(snapshot.answers)) === JSON.stringify(operation.answers) && snapshot.score === operation.score;
  const newerEdits = revision > operation.revision;
  if (replay) {
    apply(snapshot, newerEdits);
    pendingMutation = null;
    dirty = snapshot.status === 'in_progress' && newerEdits;
    message('');
  } else {
    apply(snapshot);
    pendingMutation = null;
    dirty = false;
    finishing = false;
    message('Прогресс изменился в другой вкладке. Загружена версия сервера; проверьте ответы.');
  }
}

async function flush() {
  if (busy || blocked || !state.sessionId || state.status !== 'in_progress') return;
  if (remaining() <= 0) { refresh(); return; }
  if (!pendingMutation && !dirty && !finishing) return;
  busy = true;
  const operation = pendingMutation || {
    version: state.version, answers: normalize(state.answers),
    score: scores(state.answers).reduce((sum, value) => sum + value, 0), revision, finish: finishing
  };
  pendingMutation = operation;
  save();
  try {
    const endpoint = operation.finish ? 'finish' : 'progress';
    const { response, data } = await request(`/api/sessions/${encodeURIComponent(state.sessionId)}/${endpoint}`, {
      method: operation.finish ? 'POST' : 'PUT',
      headers: { ...auth(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ version: operation.version, answers: operation.answers, score: operation.score })
    });
    if ([401, 403, 404].includes(response.status)) { unavailable(); return; }
    if (response.status === 409 && data?.detail?.code === 'version_conflict') {
      resolveConflict(data.detail.session, operation);
    } else if (response.ok) {
      const newerEdits = revision > operation.revision;
      apply(data, newerEdits);
      pendingMutation = null;
      dirty = data.status === 'in_progress' && newerEdits;
      message('');
    } else {
      throw Error('request failed');
    }
    save();
    if (response.status === 409 || data.status !== 'in_progress') render();
  } catch {
    message(operation.finish ? 'Не удалось подтвердить отправку. Повторяем запрос; не закрывайте страницу.' :
      'Не удалось сохранить прогресс на сервере. Повторяем попытку.');
    save();
  } finally {
    busy = false;
    if (!blocked && state.status === 'in_progress' && (dirty || pendingMutation || finishing)) schedule(2500);
  }
}

async function refresh() {
  if (busy || blocked || !state.sessionId) return;
  busy = true;
  lastRefresh = performance.now();
  const oldVersion = state.version;
  const wasStarted = state.startedAt;
  try {
    const { response, data } = await request(`/api/sessions/${encodeURIComponent(state.sessionId)}`, { headers: auth() });
    if ([401, 403, 404].includes(response.status)) { unavailable(); return; }
    if (!response.ok || !valid(data)) throw Error('request failed');
    if (data.status !== 'in_progress') {
      apply(data);
    } else if (pendingMutation) {
      // Повторяем неопределённый запрос через CAS, чтобы отличить свой ответ от чужого.
      clockBase = data.serverNow;
      clockMark = performance.now();
      state.teamName = data.teamName;
      state.startedAt = data.startedAt;
      state.endAt = data.endAt;
    } else if (dirty && data.version === state.version) {
      apply(data, true);
    } else if (dirty && data.version !== state.version) {
      apply(data);
      dirty = false;
      finishing = false;
      message('Прогресс изменился в другой вкладке. Загружена версия сервера; проверьте ответы.');
    } else {
      apply(data);
      message('');
    }
    save();
    if (!wasStarted || data.status !== 'in_progress' || (!pendingMutation && data.version !== oldVersion)) render();
  } catch {
    message('Нет связи с сервером. Проверяем состояние сессии повторно.');
  } finally {
    busy = false;
    if (!blocked && state.status === 'in_progress' && (dirty || pendingMutation || finishing)) schedule();
  }
}

async function register(name) {
  if (busy) return;
  const normalizedName = name.normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('ru-RU');
  const pendingKey = PENDING_KEY + encodeURIComponent(normalizedName);
  let pending;
  try {
    pending = JSON.parse(localStorage.getItem(pendingKey));
    sessionStorage.setItem(DRAFT_KEY, sessionStorage.getItem(DRAFT_KEY) || '{}');
    if (!pending) {
      if (!crypto.randomUUID) throw Error('secure random unavailable');
      pending = { name, key: crypto.randomUUID() };
      localStorage.setItem(pendingKey, JSON.stringify(pending));
    }
  } catch {
    document.getElementById('startError').textContent = 'Для начала игры необходимо безопасное хранилище браузера.';
    return;
  }
  busy = true;
  const button = document.querySelector('#startForm button');
  button.disabled = true;
  try {
    const { response, data } = await request('/api/sessions', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': pending.key },
      body: JSON.stringify({ teamName: pending.name })
    });
    if (response.status === 404) {
      localStorage.removeItem(pendingKey);
      document.getElementById('startError').textContent = 'Прежняя сессия удалена. Нажмите кнопку ещё раз, чтобы начать новую.';
      return;
    }
    if (response.status === 409 && data?.detail?.code === 'name_taken') {
      localStorage.removeItem(pendingKey);
      document.getElementById('startError').textContent = 'Это название команды уже занято.';
      return;
    }
    if (!response.ok || !valid(data) || typeof data.sessionToken !== 'string' || !data.sessionToken) throw Error('request failed');
    state = defaults();
    state.sessionToken = data.sessionToken;
    apply(data);
    if (save()) {
      localStorage.setItem(KEY, JSON.stringify({ gameId: 'case-001', sessionId: state.sessionId, sessionToken: state.sessionToken }));
      localStorage.removeItem(pendingKey);
      message('');
    }
    render();
  } catch {
    document.getElementById('startError').textContent = 'Не удалось начать игру. Повторите попытку с тем же названием команды.';
  } finally {
    busy = false;
    if (button.isConnected) button.disabled = false;
  }
}

/* Общие элементы экранов */
function btn(label, action, kind = 'secondary') {
  return `<button type="button" class="btn ${kind}" data-action="${action}">${label}</button>`;
}

function nav() {
  const steps = [['legend', 'Легенда'], ['materials', 'Материалы'], ['tasks', 'Задания']];
  return `
    <nav class="stepnav" aria-label="Разделы расследования">
      ${steps.map(([id, label]) => `
        <button type="button" data-screen="${id}" ${state.currentScreen === id ? 'aria-current="page"' : ''}>
          ${label}
        </button>
      `).join('')}
    </nav>`;
}

function renderStart() {
  return `
    <section class="screen hero" id="section-start" aria-label="Начало расследования">
      <img class="hero-image" width="1672" height="941" src="./assets/case-cover.png" alt="Дело № 001. Загадка исчезнувшего релиза">
      <img class="hero-overview" width="1672" height="941" src="./assets/case-cover.png" alt="" aria-hidden="true">
      <div class="hero-panel card">
        <p class="hero-description">У команды 15 минут, чтобы изучить цифровые улики, восстановить события и вынести вердикт.</p>
        <form id="startForm">
          <label class="formrow">
            Название команды
            <input type="text" name="team" maxlength="60" autocomplete="off" required placeholder="Например, Команда Искра" value="${esc(state.teamName)}">
          </label>
          <div class="error" id="startError" role="alert"></div>
          <button class="btn" type="submit">Начать расследование</button>
        </form>
        <p class="hero-note">Таймер запустится после подтверждения сервером. Прогресс сохраняется на сервере.</p>
      </div>
    </section>`;
}

const people = [
  ["🐈", "Макс Кодиков", "Backend Developer · @max.dev", "a-orange"],
  ["🐈", "Кот Котовый", "Lead QA · @kot.kotovyi", "a-gray"],
  ["🐱", "Алиса Текстова", "Business Analyst · @alice.ba", "a-white"],
  ["🐈‍⬛", "Вера Деплой", "Release Engineer · @vera.deploy", "a-black"],
  ["▣", "ReleaseBot", "Automation Bot · @release.bot", "a-bot"]
];

function avatar([icon, , , theme]) {
  return `<span class="avatar ${theme}" aria-hidden="true">${icon}</span>`;
}

function renderLegend() {
  const [heading, ...paragraphs] = legendMarkdown.trim().replace(/\n\n---$/, '').split(/\n\n/);
  return `
    <section class="screen" id="section-legend">
      <div class="eyebrow">01 / Вводная</div>
      <h1>Легенда и правила</h1>
      ${nav()}
      <div class="card prose">
        <h2>${inline(heading.slice(3))}</h2>
        <p>${inline(paragraphs.join(' '))}</p>
      </div>
      <section class="cast">
        <h2>Действующие лица</h2>
        <p class="muted">Вымышленные персонажи игрового сюжета.</p>
        <div class="people">
          ${people.map(person => `
            <div class="person">
              ${avatar(person)}
              <strong>${person[1]}</strong>
              <small>${person[2]}</small>
            </div>
          `).join('')}
        </div>
      </section>
      <div class="card">
        <h3>Как играть</h3>
        <ol>
          <li>Изучите восемь основных улик и два дополнительных материала.</li>
          <li>Ответьте на пять заданий. К уликам можно возвращаться в любое время.</li>
          <li>Отправьте ответы до окончания 15 минут. После отправки изменить их нельзя.</li>
        </ol>
        <p class="muted">Правильные ответы и разбор появятся после завершения расследования.</p>
      </div>
      <div class="actions">${btn('Открыть материалы', 'materials', '')}</div>
    </section>`;
}

const sources = [
  ["tracker", "Трекер задач · REL-280"],
  ["chat", "Корпоративный чат · CI/CD"],
  ["qa", "QA-система · отчёт"],
  ["document", "Документ · release notes"],
  ["chat", "Корпоративный чат · #release-2-8-0"],
  ["log", "Системный журнал · AUTO-REL-04"],
  ["board", "Рабочая доска · Product Release Board"],
  ["deploy", "CI/CD · Production deployments"],
  ["monitor", "Мониторинг · Production Health"],
  ["archive", "Архив релизов · REL-270"]
];

function materialParts() {
  const heading = /^## (?:УЛИКА №|ЛОЖНЫЙ СЛЕД №)/;
  return materialsMarkdown.split(/(?=^## (?:УЛИКА №|ЛОЖНЫЙ СЛЕД №))/m)
    .filter(part => heading.test(part.trim()));
}

function renderMaterialBody(part, index) {
  // Меняется только видимый заголовок; исходный текст и привязка ответов сохранены.
  const number = String(index + 1).padStart(2, '0');
  const displayPart = part.replace(/^## (?:УЛИКА|ЛОЖНЫЙ СЛЕД) № \d+\. /, '## ' + number + ' — ');
  let content = markdown(displayPart)
    .replace('<h3>', '<h2 id="material-title-' + (index + 1) + '">')
    .replace('</h3>', '</h2>');
  if (index === 0) {
    content = content.replace('<div class="tablewrap">',
      '<div class="tablewrap" tabindex="0" role="region" aria-label="Связанные задачи">');
  }
  // Вложенные карточки отделяются по уже существующим названиям вложений.
  const attachmentClasses = {
    'Прикреплённая карточка CI/CD:': 'ci',
    'Прикреплённый QA-отчёт:': 'qa-report',
    'Прикреплённый документ:': 'document-card'
  };
  content = content.replace(/(<p><strong>(Прикреплённая карточка CI\/CD:|Прикреплённый QA-отчёт:|Прикреплённый документ:)<\/strong><\/p>)([\s\S]*?)(?=<p><strong>Время завершения|$)/g,
    (match, title, label, body) => '<div class="attachment ' + attachmentClasses[label] + '">' + title + body + '</div>');
  // Группируем соседние пары «поле: значение», не меняя самих данных.
  content = content.replace(/(?:<p><strong>[^<]+:<\/strong>[^<]+<\/p>){2,}/g,
    group => '<div class="metadata">' + group + '</div>');
  content = content.replace(/(<td>)(PASSED|CREATED|NOT STARTED|Done|DONE|READY|NOT PUBLISHED|NOT PERFORMED|SUCCESS|NOT FOUND|HEALTHY|ON|YES|NO)(<\/td>)/g,
    '$1<span class="status">$2</span>$3');
  content = content.replace(/<p><strong>([^<]*?@([\w.]+)[^<]*)<\/strong><\/p>\s*<blockquote>([\s\S]*?)<\/blockquote>/g,
    (match, heading, handle, message) => {
      const person = people.find(entry => entry[2].endsWith('@' + handle));
      if (!person) return match;
      return `
        <div class="message">
          ${avatar(person)}
          <div class="message-body">
            <p><strong>${heading}</strong></p>
            <blockquote>${message}</blockquote>
          </div>
        </div>`;
    });
  return content;
}

function renderMaterials() {
  const parts = materialParts();
  const cards = parts.map((part, index) => {
    const [theme, source] = sources[index];
    const number = index + 1;
    const label = String(number).padStart(2, '0');
    return `
      <article class="material ${theme}" id="material-${number}" aria-labelledby="material-title-${number}">
        <div class="sourcebar"><span>${esc(source)}</span><span>${label} / ${parts.length}</span></div>
        <div class="prose">${renderMaterialBody(part, index)}</div>
      </article>`;
  });
  const tabs = cards.map((card, index) => {
    const number = index + 1;
    return `
      <button type="button" class="material-tab" role="tab"
        id="material-tab-${number}" aria-controls="material-panel-${number}"
        aria-selected="${index === 0}" tabindex="${index === 0 ? 0 : -1}"
        aria-label="Материал ${number}">${number}</button>`;
  });
  const panels = cards.map((card, index) => {
    const number = index + 1;
    return `
      <div class="material-panel" role="tabpanel" id="material-panel-${number}"
        aria-labelledby="material-tab-${number}" tabindex="0"${index === 0 ? '' : ' hidden'}>
        ${card}
      </div>`;
  });
  return `
    <section class="screen" id="section-materials">
      <div class="eyebrow">02 / Досье</div>
      <div class="section-title">
        <h1>Материалы дела</h1>
        <span class="muted">${parts.length} материалов</span>
      </div>
      ${nav()}
      <p class="lead">Все материалы открыты сразу. Сопоставляйте записи разных систем и временные отметки.</p>
      <div class="material-tabs" role="tablist" aria-label="Материалы дела">${tabs.join('')}</div>
      ${panels.join('')}
      <div class="actions">${btn('Перейти к заданиям', 'tasks', '')}</div>
    </section>`;
}

const events = [
  ["А", "Рабочая доска обновилась и скрыла завершённую карточку."],
  ["Б", "Аналитик завершил задачу с заметками к релизу."],
  ["В", "Автоматизация перевела родительскую карточку в Completed."],
  ["Г", "Разработчик завершил задачу по подготовке сборки."],
  ["Д", "Тестировщик завершил проверку и закрыл задачу."]
];

const task2 = [
  ["А", "Карточку удалил один из участников команды после завершения работы."],
  ["Б", "Карточку переместили в архив после публикации заметок к релизу."],
  ["В",
    "Автоматизация перевела карточку в Completed после завершения связанных задач, а фильтр рабочей доски скрыл завершённую карточку."],
  ["Г", "Релиз успешно развернули в Production, после чего карточка автоматически исчезла."]
];

const task3 = [
  [
    "Утверждение 1",
    "Pipeline завершился успешно. Значит, релиз уже выпущен.",
    [
      ["А","Неверно: сборка подготовлена, артефакт создан, но развёртывание не начиналось."],
      ["Б","Верно: успешная сборка автоматически означает выпуск релиза."],
      ["В","Нельзя определить: статус Pipeline не имеет отношения к выпуску."]
    ]
  ],
  [
    "Утверждение 2",
    "Мониторинг Production показывает зелёные показатели. Значит, версия 2.8.0 работает в Production.",
    [
      ["А","Верно: стабильный мониторинг подтверждает выпуск последней версии."],
      ["Б","Нельзя определить: мониторинг не показывает никаких сведений о версии."],
      ["В","Неверно: мониторинг показывает состояние Production, а текущая версия — 2.7.4."]
    ]
  ],
  [
    "Утверждение 3",
    "Заметки к релизу имеют статус READY. Значит, релиз опубликован.",
    [
      ["А","Верно: статус READY означает, что релиз доступен пользователям."],
      ["Б","Неверно: документ подготовлен, но его статус публикации — NOT PUBLISHED."],
      ["В","Нельзя определить: заметки не связаны с релизом."]
    ]
  ],
  [
    "Общий вывод",
    "После проверки трёх утверждений выберите общий вывод:",
    [
      ["А","Завершение всех подготовительных задач и готовность документов подтверждают, что релиз выпущен."],
      ["Б","Подготовка сборки, тестирование в Staging и готовность заметок сами по себе не подтверждают выпуск. Для подтверждения нужен успешный Deployment в Production."],
      ["В","Если карточка получила статус Completed, дополнительные подтверждения выпуска не нужны."]
    ]
  ]
];

const task4q = [
  ["Почему нельзя считать, что релиз 2.8.0 был развёрнут в Production к моменту исчезновения карточки?",
    "Выберите улику, которая подтверждает отсутствие успешного Production Deployment."],
  ["Почему родительская карточка REL-280 получила статус Completed?",
    "Выберите улику, которая показывает условие запуска автоматизации и её действие."],
  ["Почему карточка перестала отображаться на рабочей доске?",
    "Выберите улику, которая подтверждает действие фильтра и отсутствие удаления или архивирования."]
];

const task4seq = [
  ["А", "Карточку скрыли с доски → релиз развернули → автоматизация закрыла задачи."],
  ["Б",
    "Все связанные подготовительные задачи завершились → автоматизация изменила статус родительской карточки → фильтр скрыл завершённую карточку с доски."],
  ["В", "Релиз опубликовали → карточку архивировали → задачи получили статус Done."]
];

const task5 = [
  ["А", "Убрать фильтр завершённых задач с рабочей доски, чтобы карточки всегда оставались видимыми."],
  ["Б", "Запретить автоматическое изменение статусов карточек при завершении связанных задач."],
  ["В", "Разрешить только Release Engineer вручную менять статус родительской карточки."],
  ["Г", "Сделать получение статуса Completed зависимым от подтверждённого успешного развёртывания нужной версии в Production."]
];

function options(name, items, value) {
  return `
    <div class="options">
      ${items.map(([key, label]) => `
        <label class="option">
          <input type="radio" name="${name}" value="${key}" ${value === key ? 'checked' : ''}>
          <span><strong>${key}.</strong> ${label}</span>
        </label>
      `).join('')}
    </div>`;
}

function field(title, body) {
  return `<fieldset class="question"><legend>${title}</legend>${body}</fieldset>`;
}

function taskCard(number, title, max, body) {
  return `
    <section class="task" id="task-${number}">
      <div class="taskhead">
        <h2>Задание № ${number}. ${title}</h2>
        <span class="max">${max} балл${max === 2 ? 'а' : 'ов'}</span>
      </div>
      ${body}
    </section>`;
}

function renderTasks() {
  const answers = state.answers;

  const order = `
    <p>Расположите события в правильной последовательности — от самого раннего к самому позднему.</p>
    <div class="order">
      ${events.map(([key, label], index) => `
        <label class="orderrow">
          <select data-order="${key}" aria-label="Позиция события ${key}">
            <option value="">—</option>
            ${[1, 2, 3, 4, 5].map(position => `
              <option value="${position}" ${answers.task1[index] === position ? 'selected' : ''}>${position}</option>
            `).join('')}
          </select>
          <span><strong>${key}.</strong> ${label}</span>
        </label>
      `).join('')}
    </div>
    <p class="muted">Назначьте каждому событию отдельную позицию от 1 до 5.</p>`;

  const cause = field(
    'Выберите наиболее точное объяснение непосредственной причины исчезновения карточки с рабочей доски.',
    options('task2', task2, answers.task2)
  );

  const facts = `
    <p>Определите, какие из утверждений подтверждаются материалами дела. Для каждого утверждения выберите один вариант.</p>
    ${task3.map(([title, description, items], index) =>
      field(title, `<p>${description}</p>${options('task3-' + index, items, answers.task3[index])}`)
    ).join('')}`;

  const evidence = `
    <p>Восстановите цепочку событий и подтвердите каждый вывод конкретной уликой.</p>
    ${task4q.map(([title, hint], index) => field(`${index + 1}. ${title}`, `
      <p>${hint}</p>
      <select data-evidence="${index}" aria-label="Номер материала для вопроса ${index + 1}">
        <option value="">Выберите материал</option>
        ${Array.from({ length: 10 }, (_, i) => {
          const number = i + 1;
          return `<option value="${number}" ${Number(answers.task4[index]) === number ? 'selected' : ''}>
            Материал № ${number}
          </option>`;
        }).join('')}
      </select>
    `)).join('')}
    ${field('4. Восстановите причинную последовательность',
      `<p>Выберите правильную цепочку:</p>${options('task4-seq', task4seq, answers.task4[3])}`
    )}`;

  const process = field(
    'Какое изменение процесса предотвратило бы повторение подобной ситуации?',
    `<p>Выберите наиболее правильное решение.</p>${options('task5', task5, answers.task5)}`
  );

  return `
    <section class="screen" id="section-tasks">
      <div class="eyebrow">03 / Версия команды</div>
      <h1>Задания</h1>
      ${nav()}
      <div class="notice">Ответы можно менять до отправки или окончания времени. Промежуточная проверка не проводится.</div>
      ${taskCard(1, 'Восстановите хронологию', 6, order)}
      ${taskCard(2, 'Почему карточка исчезла?', 4, cause)}
      ${taskCard(3, 'Проверьте факты', 4, facts)}
      ${taskCard(4, 'Соберите доказательства', 4, evidence)}
      ${taskCard(5, 'Найдите процессную ошибку', 2, process)}
      <div class="actions">
        ${btn('Вернуться к материалам', 'materials')}
        ${btn('Завершить расследование', 'confirm', '')}
      </div>
    </section>`;
}

/* Итоги расследования */
function scores(answers) {
  const correctOrder = ['Г', 'Д', 'Б', 'В', 'А'];
  const orderScore = correctOrder.reduce((score, key, index) =>
    score + (Number(answers.task1[events.findIndex(event => event[0] === key)]) === index + 1 ? 1 : 0), 0);
  const factScore = ['А', 'В', 'Б', 'Б'].reduce((score, key, index) =>
    score + (answers.task3[index] === key ? 1 : 0), 0);
  const evidenceScore = [8, 6, 7, 'Б'].reduce((score, key, index) =>
    score + (String(answers.task4[index]) === String(key) ? 1 : 0), 0);

  return [
    orderScore + (orderScore === 5 ? 1 : 0),
    answers.task2 === 'В' ? 4 : 0,
    factScore,
    evidenceScore,
    answers.task5 === 'Г' ? 2 : 0
  ];
}

function submit() {
  if (state.status !== 'in_progress' || finishing || blocked || remaining() <= 0) {
    if (remaining() <= 0) refresh();
    return;
  }
  finishing = true;
  save();
  render();
  if (!busy) flush();
}

function renderConfirm() {
  return `
    <section class="screen" id="section-confirm">
      <div class="eyebrow">04 / Отправка</div>
      <div class="card">
        <h1>Передать результаты?</h1>
        <p class="lead">Вы готовы передать результаты расследования?</p>
        <p>После отправки изменить ответы будет нельзя. Сайт проверит решение и покажет итоговый результат.</p>
        <div class="actions">
          ${finishing ? '<p class="muted">Подтверждаем отправку…</p>' : btn('Вернуться к заданиям', 'tasks') + btn('Отправить ответы', 'submit', '')}
        </div>
      </div>
    </section>`;
}

function renderResult() {
  const values = state.taskScores || scores(state.answers);
  const max = [6, 4, 4, 4, 2];
  const titles = ['Хронология', 'Причина исчезновения', 'Проверка фактов', 'Доказательства', 'Процессная ошибка'];
  const outcome = state.status === 'timed_out'
    ? 'Время истекло, выбранные ответы зафиксированы.'
    : 'Ответы отправлены.';

  return `
    <section class="screen" id="section-result">
      <div class="eyebrow">05 / Индивидуальный результат</div>
      <h1>Дело раскрыто!</h1>
      <p class="lead">Команда «${esc(state.teamName)}»</p>
      <div class="bigscore">${state.score} / 20</div>
      <p class="muted">
        ${Math.round(state.score / 20 * 100)}% · ${outcome}
        Время завершения: ${new Date(state.submittedAt).toLocaleTimeString('ru-RU')}
      </p>
      <div class="resultgrid">
        ${titles.map((title, index) => `
          <div class="scorebox">
            <small>Задание № ${index + 1}</small>
            <h3>${title}</h3>
            <strong>${values[index]} / ${max[index]}</strong>
          </div>
        `).join('')}
      </div>
      <div class="actions">${btn('Открыть финальный разбор', 'debrief', '')}</div>
    </section>`;
}

function renderDebrief() {
  return `
    <section class="screen" id="section-debrief">
      <div class="eyebrow">06 / Раскрытие дела</div>
      <h1>Финальный разбор</h1>
      <p class="lead">Команда «${esc(state.teamName)}» · ${state.score} / 20 баллов</p>
      <div class="debrief-flow">
        <div class="card prose">
          <h2>Правильные ответы</h2>
          <ol>
            <li><strong>Хронология:</strong> Г → Д → Б → В → А.</li>
            <li><strong>Причина исчезновения:</strong> В.</li>
            <li><strong>Проверка фактов:</strong> А, В, Б; общий вывод — Б.</li>
            <li><strong>Доказательства:</strong> улика № 8, улика № 6, улика № 7; последовательность — Б.</li>
            <li><strong>Процессная ошибка:</strong> Г.</li>
          </ol>
        </div>
        <div class="card prose">${markdown(finaleMarkdown)}</div>
        <p class="verdict">Система отметила завершение подготовки, а не фактический выпуск релиза</p>
        <p class="muted">Материалы подтверждают состояние системы на момент аудита 10:21:30 и не исключают более поздний выпуск.</p>
      </div>
      <div class="actions">${btn('Вернуться к результату', 'result')}</div>
    </section>`;
}

const renderers = {
  start: renderStart,
  legend: renderLegend,
  materials: renderMaterials,
  tasks: renderTasks,
  confirm: renderConfirm,
  result: renderResult,
  debrief: renderDebrief
};

function render() {
  if (blocked) {
    app.innerHTML = '<section class="screen"><div class="card"><h1>Сессия недоступна</h1><p>Обратитесь к организатору.</p></div></section>';
    document.getElementById('floatnav').hidden = true;
    return;
  }
  let page = state.currentScreen;
  if (state.status !== 'in_progress' && !['result', 'debrief'].includes(page)) page = 'result';
  const renderScreen = Object.hasOwn(renderers, page) ? renderers[page] : renderStart;
  document.getElementById('teamHeader').textContent = state.startedAt ? state.teamName : '';
  app.innerHTML = renderScreen();
  document.getElementById('floatnav').hidden = renderScreen === renderStart;
  tick();
}

/* Навигация по вкладкам материалов */
function selectMaterialTab(tab, fromKeyboard = false) {
  const list = tab.closest('.material-tabs');
  const section = tab.closest('#section-materials');
  if (!list || !section) return;
  list.querySelectorAll('[role="tab"]').forEach(item => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    item.toggleAttribute('data-keyboard-focus', selected && fromKeyboard);
    const panel = section.querySelector('#' + item.getAttribute('aria-controls'));
    if (panel) panel.hidden = !selected;
  });
  tab.focus({ preventScroll: true });
  const listRect = list.getBoundingClientRect();
  const tabRect = tab.getBoundingClientRect();
  const left = listRect.left + list.clientLeft;
  const right = left + list.clientWidth;
  const focusInset = 5; // 3px outline and 2px offset.
  if (tabRect.left - focusInset < left) list.scrollLeft += tabRect.left - focusInset - left;
  else if (tabRect.right + focusInset > right) list.scrollLeft += tabRect.right + focusInset - right;
}

app.addEventListener('click', event => {
  const tab = event.target.closest('.material-tabs [role="tab"]');
  if (tab) selectMaterialTab(tab);
});

app.addEventListener('keydown', event => {
  const tab = event.target.closest('.material-tabs [role="tab"]');
  if (!tab) return;
  const tabs = Array.from(tab.closest('.material-tabs').querySelectorAll('[role="tab"]'));
  const current = tabs.indexOf(tab);
  let next;
  if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
  else if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
  else if (event.key === 'Home') next = 0;
  else if (event.key === 'End') next = tabs.length - 1;
  else return;
  event.preventDefault();
  selectMaterialTab(tabs[next], true);
});

/* Запуск игры, переходы и ввод ответов */
app.addEventListener('submit', event => {
  if (event.target.id !== 'startForm') return;
  event.preventDefault();

  const name = event.target.elements.team.value.trim().replace(/\s+/g, ' ');
  if (!name) {
    document.getElementById('startError').textContent = 'Введите название команды.';
    return;
  }

  register(name);
});

app.addEventListener('click', event => {
  const button = event.target.closest('[data-action],[data-screen]');
  if (!button) return;
  const action = button.dataset.action || button.dataset.screen;
  if (action === 'submit') {
    submit();
    return;
  }
  if (finishing || (state.status !== 'in_progress' && !['result', 'debrief'].includes(action))) return;
  screen(action);
});

app.addEventListener('change', event => {
  if (!event.target.closest('#section-tasks')) return;
  if (state.status !== 'in_progress' || finishing || blocked || remaining() <= 0) { render(); refresh(); return; }
  const control = event.target;
  const answers = state.answers;

  if (control.dataset.order) {
    const position = Number(control.value) || null;
    if (position) {
      document.querySelectorAll('[data-order]').forEach(other => {
        if (other !== control && Number(other.value) === position) {
          other.value = '';
          answers.task1[events.findIndex(item => item[0] === other.dataset.order)] = null;
        }
      });
    }
    answers.task1[events.findIndex(item => item[0] === control.dataset.order)] = position;
  } else if (control.dataset.evidence !== undefined) {
    answers.task4[Number(control.dataset.evidence)] = control.value ? Number(control.value) : null;
  } else if (control.name === 'task2' || control.name === 'task5') {
    answers[control.name] = control.value;
  } else if (control.name.startsWith('task3-')) {
    answers.task3[Number(control.name.slice(-1))] = control.value;
  } else if (control.name === 'task4-seq') {
    answers.task4[3] = control.value;
  }

  dirty = true; revision++; save(); schedule();
});

document.getElementById('toTop').addEventListener('click', () => window.scrollTo({ top: 0 }));
/* Черновик вкладки имеет приоритет над последней общей сессией браузера. */
try {
  const draft = JSON.parse(sessionStorage.getItem(DRAFT_KEY));
  const shared = JSON.parse(localStorage.getItem(KEY));
  const credentials = draft?.sessionId && draft?.sessionToken ? draft : shared;
  if (credentials?.gameId === 'case-001' || (credentials === draft && credentials?.sessionToken)) {
    if (typeof credentials.sessionId === 'string' && typeof credentials.sessionToken === 'string' && credentials.sessionToken) {
      state = defaults();
      state.sessionId = credentials.sessionId;
      state.sessionToken = credentials.sessionToken;
      if (draft?.sessionId === state.sessionId && draft.answers) {
        state.answers = normalize(draft.answers);
        state.version = draft.version;
        state.currentScreen = draft.currentScreen;
        dirty = Boolean(draft.dirty);
        revision = draft.revision || 0;
        pendingMutation = draft.pendingMutation || null;
        finishing = Boolean(draft.finishing);
      }
    }
  }
} catch { /* Повреждённые данные не создают новую сессию. */ }
if (!state) state = defaults();
window.addEventListener('storage', event => {
  if (event.key === KEY && state.sessionId) refresh();
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) { tick(); refresh(); }
});
setInterval(tick, 500);
setInterval(() => {
  if (!document.hidden && !blocked && state.sessionId && state.status === 'in_progress') refresh();
}, 15000);
render();
if (state.sessionId) refresh();
'use strict';

function techFields(source, labels) {
  return artifactFields(labels.filter(label => source.fields[label] !== undefined).map(label => [label, source.fields[label]]));
}

function techSection(material, name) {
  return material.sections[name] || { fields: {}, rows: [], items: [], quotes: [] };
}

function techValue(value) {
  return /^(PASSED|CREATED|DONE|SUCCESS|COMPLETE|HEALTHY|READY|ON|YES|NO|NOT .+|0)$/.test(value) ? artifactStatus(value) : esc(value);
}

function techDetails(rows) {
  return `<dl class="tech-details">${rows.slice(1).map(row => `<div${(row[1] || '').length > 18 ? ' class="tech-long-value"' : ''}><dt>${esc(row[0])}</dt><dd>${techValue(row[1] || '')}</dd></div>`).join('')}</dl>`;
}

function techRowValue(rows, label) {
  const row = rows.slice(1).find(entry => entry[0] === label);
  return row ? row[1] : '';
}

function techTimeline(rows) {
  return `<ol class="tech-timeline">${rows.slice(1).map(row => `<li><span class="tech-time">${artifactTime(row[0])}</span><span>${esc(row[1] || '')}</span></li>`).join('')}</ol>`;
}

function techItems(items) {
  return `<ul class="tech-audit">${items.map(item => {
    const split = item.indexOf(':');
    const value = item.slice(split + 1).trim();
    return split < 0 ? `<li>${esc(item)}</li>` : `<li${value.length > 18 ? ' class="tech-long-value"' : ''}><span>${esc(item.slice(0, split))}</span><strong>${techValue(value)}</strong></li>`;
  }).join('')}</ul>`;
}

function techPanel(title, content) {
  return `<section class="artifact-surface tech-panel"><h4 class="artifact-section-title">${esc(title)}</h4>${content}</section>`;
}

function renderTechnicalMaterial(material, number) {
  const field = material.fields;
  const section = name => techSection(material, name);
  const chat = title => renderMaterialChat({ channel: field['Канал'], messages: material.messages, title });

  if (number === 3) {
    const report = section('Прикреплённый QA-отчёт');
    return `<div class="tech-artifact"><header class="tech-header"><div><p class="artifact-label">QA-система</p><h3 class="artifact-title">Результаты проверки сборки</h3></div><span class="tech-id artifact-mono">${esc(field['Report ID'] || '')}</span></header>
      <div class="artifact-surface tech-panel">${techFields(material, ['Build', 'Version', 'Environment'])}<h4 class="artifact-section-title">Результаты QA</h4>${techDetails(report.rows)}<p class="tech-completion"><span>Время завершения задачи QA-280</span> ${artifactTime(field['Время завершения задачи QA-280'] || '')}</p></div>
      ${chat('Сообщение тестировщика')}</div>`;
  }
  if (number === 6) {
    return `<div class="tech-artifact"><header class="tech-header"><div><h3 class="artifact-title">${esc(field['Rule name'] || '')}</h3><span class="tech-id artifact-mono">${esc(field['Rule ID'] || '')}</span></div><div class="tech-header-status"><span class="artifact-label">Result</span> ${artifactStatus(field.Result || '')}</div></header>
      ${techFields(material, ['Target card', 'Execution ID', 'Executed by'])}
      <div class="tech-pair">${['Условие запуска', 'Действие'].map(name => techPanel(name, section(name).quotes.map(quote => `<blockquote class="tech-rule">${esc(quote)}</blockquote>`).join(''))).join('')}</div>
      ${techPanel('Журнал событий', techTimeline(section('Журнал событий').rows))}
      ${techPanel('Результат выполнения правила', techItems(section('Результат выполнения правила').items))}</div>`;
  }
  if (number === 7) {
    return `<div class="tech-artifact"><header class="tech-header"><div><p class="artifact-label">Рабочая доска</p><h3 class="artifact-title">${esc(field['Доска'] || '')}</h3></div></header>
      ${techPanel('Настройки фильтра на момент обновления', techDetails(section('Настройки фильтра на момент обновления').rows))}
      ${techPanel('Журнал событий', techTimeline(section('Журнал событий').rows))}
      ${techPanel('Результат проверки карточки', techItems(section('Результат проверки карточки').items))}</div>`;
  }
  if (number === 8) {
    const search = section('Результат поиска').rows;
    const last = section('Последнее успешное развёртывание в Production').rows;
    const searchValue = label => techRowValue(search, label);
    const lastValue = label => techRowValue(last, label);
    return `<div class="tech-artifact"><header class="tech-header"><div><p class="artifact-label">История развёртываний</p><h3 class="artifact-title">${esc(field.Project || '')} · ${esc(field.Environment || '')}</h3></div></header>
      ${techFields(material, ['Snapshot time', 'Audit period', 'Audit status', 'Фильтр'])}
      <section class="artifact-surface tech-panel"><h4 class="artifact-section-title">Результат поиска</h4><div class="tech-search-summary"><div><span class="artifact-label">Release reference</span><strong class="artifact-mono">${esc(searchValue('Release reference'))}</strong></div><div><span class="tech-count">${esc(searchValue('Deployment records matching REL-280'))}</span><span>Deployment records matching REL-280</span></div></div>${techDetails([search[0], ...search.slice(3)])}</section>
      <section class="artifact-surface tech-panel"><h4 class="artifact-section-title">Последнее успешное развёртывание в Production</h4><dl class="tech-deployment">${['Version', 'Environment', 'Result', 'Deployment time'].map(label => `<div><dt>${esc(label)}</dt><dd>${label === 'Deployment time' ? artifactTime(lastValue(label)) : techValue(lastValue(label))}</dd></div>`).join('')}</dl></section>
      <div class="artifact-surface tech-panel">${techFields(material, ['Текущая версия в Production на 10:21:30', 'Ограничение вывода'])}</div></div>`;
  }
  if (number === 9) {
    const metric = label => techRowValue(material.rows, label);
    return `<div class="tech-artifact"><header class="tech-header"><div><h3 class="artifact-title">${esc(field.Dashboard || '')}</h3><div class="tech-snapshot"><span>Время снимка</span> ${artifactTime(field['Время снимка'] || '')}</div></div></header>
      <section class="artifact-surface tech-panel"><div class="tech-metric-summary"><div><span class="artifact-label">System status</span> ${techValue(metric('System status'))}</div><div><span class="artifact-label">Current production version</span> <strong class="artifact-mono">${esc(metric('Current production version'))}</strong></div></div><div class="tech-metrics">${['Availability', 'Error rate', 'Response time'].map(label => `<div class="tech-metric"><span>${esc(label)}</span><strong>${esc(metric(label))}</strong></div>`).join('')}</div></section>${chat('Сообщение в чате')}</div>`;
  }
  if (number === 10) {
    return `<div class="tech-artifact"><header class="tech-header"><div><h3 class="artifact-title">Release ${esc(field.Release || '')}</h3></div><span class="tech-id artifact-mono">${esc(field['Card ID'] || '')}</span></header>
      ${techPanel('История событий', techTimeline(section('История событий').rows))}
      ${techPanel('Дополнительная информация', techItems(section('Дополнительная информация').items))}</div>`;
  }
  return '';
}

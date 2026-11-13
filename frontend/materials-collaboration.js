'use strict';

function collabAttachment(material, sectionName, completionLabel, kind) {
  const section = material.sections[sectionName] || {};
  const fields = section.fields || {};
  const completion = material.fields[completionLabel] || fields[completionLabel];
  const rows = (section.rows || []).slice(1);
  const metadata = Object.entries(fields).filter(([label]) => label !== completionLabel &&
    (kind !== 'document' || (label !== 'Document ID' && label !== 'Название')));
  const result = row => `<div class="collab-result"><span>${esc(row[0])}</span>${artifactStatus(row[1])}</div>`;
  return `<section class="collab-attachment collab-${kind}" aria-label="${esc(sectionName)}">
    <h4 class="artifact-section-title">${esc(sectionName)}</h4>
    ${kind === 'document' ? `<div class="collab-document-heading"><strong>${esc(fields['Название'])}</strong><span>Document ID: <span class="artifact-mono">${esc(fields['Document ID'])}</span></span></div>` : ''}
    ${artifactFields(metadata)}
    ${kind === 'pipeline' ? `<ol class="collab-pipeline-stages">${rows.slice(0, 3).map(row => `<li><span>${esc(row[0])}</span>${artifactStatus(row[1])}</li>`).join('')}</ol><div class="collab-results">${rows.slice(3).map(result).join('')}</div>` : `<div class="collab-results">${rows.map(result).join('')}</div>`}
    ${completion ? `<div class="collab-completion"><span>${esc(completionLabel)}</span> ${artifactTime(completion)}</div>` : ''}
  </section>`;
}

function renderMaterialChat({ channel, messages, title, attachment = '' }) {
  return `<section class="collab-chat artifact-surface">
    <header class="collab-chat-header">
      ${title ? `<h3 class="artifact-title">${esc(title)}</h3>` : ''}
      ${channel ? `<div class="collab-channel"><span class="artifact-label">Канал</span> <strong>${esc(channel)}</strong></div>` : ''}
    </header>
    <div class="collab-messages">${(messages || []).map((message, index) => {
      const person = people.find(entry => entry[2].endsWith(message.handle));
      return `<article class="collab-message">
        <div class="collab-avatar">${person ? avatar(person) : ''}</div>
        <div class="collab-message-body">
          <div class="collab-message-meta"><strong>${esc(message.name)}</strong> <span>${esc(message.handle)}</span> ${artifactTime(message.time)}</div>
          <p>${esc(message.text)}</p>
          ${index === 0 ? attachment : ''}
        </div>
      </article>`;
    }).join('')}</div>
  </section>`;
}

function collabTracker(material) {
  const fields = material.fields;
  const related = material.sections['Связанные задачи'] || {};
  const info = material.sections['Дополнительная информация'] || {};
  return `<section class="collab-tracker artifact-surface">
    <div class="collab-tracker-heading"><div><span class="artifact-label">${esc('Карточка')}</span><h3 class="artifact-title"><span class="artifact-mono">${esc(fields['Карточка'])}</span> · ${esc(fields['Название'])}</h3></div><div class="collab-current-status"><span class="artifact-label">Текущий статус</span>${artifactStatus(fields['Текущий статус'])}</div></div>
    ${artifactFields([['Создана', fields['Создана']], ['Снимок карточки', fields['Снимок карточки']]])}
    <section class="collab-tasks"><h4 class="artifact-section-title">Связанные задачи</h4>
      <ul class="collab-task-list">${(related.rows || []).slice(1).map(row => `<li class="collab-task">
        <div><span class="artifact-mono collab-task-id">${esc(row[0])}</span><strong>${esc(row[1])}</strong><span class="collab-assignee">${esc((related.rows[0] || [])[2])}: ${esc(row[2])}</span></div>${artifactStatus(row[3])}
      </li>`).join('')}</ul>
    </section>
    <section class="collab-notes"><h4 class="artifact-section-title">Дополнительная информация</h4><ul>${(info.items || []).map(item => `<li>${esc(item)}</li>`).join('')}</ul></section>
  </section>`;
}

function renderCollaborationMaterial(material, number) {
  if (number === 1) return collabTracker(material);
  let attachment = '';
  if (number === 2) attachment = collabAttachment(material, 'Прикреплённая карточка CI/CD', 'Время завершения задачи DEV-280', 'pipeline');
  if (number === 4) attachment = collabAttachment(material, 'Прикреплённый документ', 'Время завершения задачи BA-280', 'document');
  const titles = { 2: 'Сообщение разработчика', 4: 'Сообщение аналитика', 5: 'Переписка о выпуске' };
  if (titles[number]) {
    return renderMaterialChat({ channel: material.fields['Канал'], messages: material.messages, title: titles[number], attachment });
  }
  return '';
}


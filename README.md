# Развёртывание «Дела № 001»

Проект работает на одном HTTPS-домене. Игра открывается по `/`, игровой API и вебхуки доступны по `/api`. Папку `artcode-detective-game` укажите как корень проекта Vercel.

## 1. Upstash

1. В [Upstash Console](https://console.upstash.com/) создайте Redis Database на плане **Free**. В базе откройте **Connect → REST** и скопируйте URL и токен с правами записи. [Документация Redis REST API](https://upstash.com/docs/redis/features/restapi)
2. В разделе **QStash** выберите регион. Из блока **Quickstart** скопируйте токен, текущий и следующий ключи подписи. Если консоль показывает региональный URL API, сохраните и его. Игра сама ставит отложенное сообщение при регистрации каждой команды. [Настройка QStash](https://upstash.com/docs/qstash/overall/getstarted)

## 2. Telegram

1. Откройте [@BotFather](https://t.me/BotFather), выполните `/newbot` и сохраните токен. [Инструкция Telegram](https://core.telegram.org/bots/tutorial)
2. Чтобы узнать свой User ID, откройте личный чат с новым ботом и отправьте `/start`. До установки вебхука вызовите `getUpdates` и возьмите число из `message.from.id` у своего сообщения. Для нескольких администраторов повторите это для каждого. [Метод getUpdates](https://core.telegram.org/bots/api#getupdates)

   В PowerShell 7 токен можно ввести без отображения на экране. Сохраните переменную в этой сессии для следующего шага.

   ```powershell
   $botToken = Read-Host 'Токен бота' -MaskInput
   (Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot${botToken}/getUpdates").result |
     ForEach-Object { $_.message.from.id }
   ```

3. Придумайте отдельный случайный секрет вебхука из латинских букв, цифр, дефисов или подчёркиваний. Добавьте его и список User ID в Vercel. После развёртывания зарегистрируйте вебхук, используя тот же секрет.

   ```powershell
   $publicUrl = 'https://ваш-проект.vercel.app'
   $webhookSecret = Read-Host 'Секрет вебхука' -MaskInput
   $payload = @{
     url = "$publicUrl/api/webhooks/telegram"
     secret_token = $webhookSecret
     allowed_updates = @('message', 'callback_query')
   } | ConvertTo-Json
   Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot${botToken}/setWebhook" -ContentType 'application/json' -Body $payload
   ```

   Ответ должен содержать `ok: true`. Действующий вебхук с тем же URL, секретом и типами обновлений `message` и `callback_query` можно оставить при обновлении backend. [Метод setWebhook](https://core.telegram.org/bots/api#setwebhook)

4. Отправьте `/start` в личном чате с ботом. При каждом вызове бот проверяет соединение с Redis. После успешной проверки он включает уведомления о начале и завершении игр и показывает постоянные кнопки «📋 Список команд» и «🏆 Общий рейтинг». При ошибке Redis бот сообщает о частичной недоступности. [Клавиатура Telegram](https://core.telegram.org/bots/api#replykeyboardmarkup)
5. Нажмите «📋 Список команд» или отправьте `/teams`. Бот присылает отдельное сообщение для каждой команды на странице. Для удаления нажмите «🗑 Удалить» под нужной командой и подтвердите действие. После подтверждения бот убирает вопрос и карточку команды, если Telegram разрешает их удалить. При отмене он убирает только вопрос. Команда `/delete` также открывает выбор команды для удаления. После удаления название можно зарегистрировать заново. Игрок на экране недоступной сессии может обновить страницу и запустить игру вручную.
6. Нажмите «🏆 Общий рейтинг», чтобы посмотреть результаты завершённых игр. Бот сортирует команды по баллам, при равенстве выше ставит команду, завершившую игру раньше. [Ограничения на удаление сообщений в Telegram](https://core.telegram.org/bots/api#deletemessage)

## 3. Vercel

Импортируйте Git-репозиторий в один проект Vercel. Если `artcode-detective-game` находится внутри репозитория, укажите её в **Root Directory**. Оставьте установку зависимостей и команды сборки по умолчанию для **FastAPI**. Frontend состоит из статических файлов. [FastAPI на Vercel](https://vercel.com/docs/frameworks/backend/fastapi)

В **Settings → Environment Variables** добавьте значения для Production.

| Переменная | Значение |
| --- | --- |
| `UPSTASH_REDIS_REST_URL` | HTTPS URL Redis REST API |
| `UPSTASH_REDIS_REST_TOKEN` | Токен Redis с правами записи |
| `QSTASH_TOKEN` | Токен QStash |
| `QSTASH_CURRENT_SIGNING_KEY` | Текущий ключ подписи QStash |
| `QSTASH_NEXT_SIGNING_KEY` | Следующий ключ подписи QStash |
| `QSTASH_URL` | URL регионального QStash API при необходимости. По умолчанию `https://qstash.upstash.io` |
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather |
| `TELEGRAM_ADMIN_IDS` | Числовые User ID через запятую |
| `TELEGRAM_WEBHOOK_SECRET` | Секрет из запроса `setWebhook` |
| `PUBLIC_BASE_URL` | Стабильный публичный HTTPS-домен, например `https://my-project.vercel.app` |

Сделайте production deployment после добавления переменных. `/api/internal/expire` и `/api/webhooks/telegram` должны быть доступны провайдерам по этому домену. При первом запуске можно сначала развернуть проект для получения постоянного домена, затем сохранить `PUBLIC_BASE_URL` и развернуть повторно.

Проверьте игру на отдельной тестовой команде. Дождитесь уведомления о старте, выберите ответ и обновите страницу. Проверьте восстановление прогресса и таймера, ручную отправку, баллы в Telegram и список `/teams`. Для проверки QStash запустите вторую команду, дождитесь сохранения ответа, закройте вкладку и после истечения 15 минут проверьте статус, уведомление и итог при повторном открытии. Логи доставки доступны в QStash Console. [Проверка доставки QStash](https://upstash.com/docs/qstash/overall/getstarted#check-message-status)

На бесплатном плане Upstash Redis доступно 500 тыс. команд в месяц, 256 МБ данных и 10 ГБ месячного трафика. Для QStash Free доступны 1 000 сообщений в день и задержка до 7 дней. Vercel Hobby предназначен для личного некоммерческого использования. Для коммерческого использования Vercel требует Pro или Enterprise. [Upstash Redis](https://upstash.com/pricing/redis) · [Upstash QStash](https://upstash.com/pricing/qstash) · [Правила Vercel](https://vercel.com/docs/limits/fair-use-guidelines#commercial-usage)

Баллы рассчитываются в браузере и могут быть подделаны клиентом. При автозавершении сохраняется последний подтверждённый сервером прогресс. После сбоя при регистрации повторите запрос с тем же названием в том же браузере. Если сервер так и не подтвердит постановку таймера, резервация названия истечёт.

Telegram Bot API не предоставляет ключ идемпотентности для отправки. Сервер резервирует уведомление до вызова Telegram, чтобы повторное завершение не отправило дубликат. При сбое в этот момент отдельное уведомление может потеряться. Сохранённые результаты доступны через `/teams`.

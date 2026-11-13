import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
EMPTY = {"task1": [], "task2": None, "task3": [None] * 4, "task4": [None] * 4, "task5": None}


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError("Missing configuration: " + name)
    return value


def now_ms() -> int:
    return int(time.time() * 1000)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def redis(*command: Any) -> Any:
    if command[0] in {'GET', 'ZREVRANGE', 'SISMEMBER'}:
        command = ('EVAL', 'return redis.call(unpack(ARGV))', 0, *command)
    response = httpx.post(env("UPSTASH_REDIS_REST_URL").rstrip("/"), headers={"Authorization": "Bearer " + env("UPSTASH_REDIS_REST_TOKEN")}, json=list(command), timeout=8)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("Invalid Redis response")
    if result.get("error"):
        raise RuntimeError("Redis command failed")
    if 'result' not in result:
        raise RuntimeError("Invalid Redis response")
    return result['result']


def eval_script(script: str, keys: list[str], args: list[Any]) -> Any:
    return redis("EVAL", script, len(keys), *keys, *args)


# Redis TIME supplies the authoritative deadline clock inside each atomic transition.
CLOCK = "local t=redis.call('TIME'); local now=t[1]*1000+math.floor(t[2]/1000); "
RESERVE = CLOCK + '''
local existing=redis.call('GET',KEYS[1]);
if existing then
 local current=redis.call('GET','game:session:'..existing)
 if current then return {'existing',existing,current} end
 return {'deleted'}
end
if redis.call('EXISTS',KEYS[2])==1 then return {'taken'} end
local s=cjson.decode(ARGV[1]); s.startedAt=now; s.endAt=now+900000;
redis.call('SET',KEYS[1],s.sessionId,'PX',900000); redis.call('SET',KEYS[2],s.sessionId,'PX',900000);
redis.call('SET',KEYS[3],cjson.encode(s),'PX',900000);
return {'created',s.sessionId,cjson.encode(s)}
'''
# The idempotency key retains its original name and token. An interrupted publish is retried.
MARK_READY = CLOCK + '''
local raw=redis.call('GET',KEYS[1]); if not raw then return nil end
local s=cjson.decode(raw)
if s.ready then return raw end
if now>=s.endAt then
 redis.call('DEL',KEYS[1])
 if redis.call('GET',s.nameKey)==s.sessionId then redis.call('DEL',s.nameKey) end
 if redis.call('GET',s.idemKey)==s.sessionId then redis.call('DEL',s.idemKey) end
 return nil
end
s.ready=true; s.messageId=ARGV[1]
redis.call('SET',KEYS[1],cjson.encode(s)); redis.call('PERSIST',s.nameKey); redis.call('PERSIST',s.idemKey)
redis.call('ZADD','game:teams',s.startedAt,s.sessionId)
return cjson.encode(s)
'''
TRANSITION = CLOCK + '''
local raw=redis.call('GET',KEYS[1]); if not raw then return {'missing'} end
local s=cjson.decode(raw)
if ARGV[1]~='' and s.tokenHash~=ARGV[1] then return {'unauthorized'} end
if not s.ready then return {'pending'} end
if s.status=='in_progress' and now>=s.endAt then
 s.status='timed_out'; s.submittedAt=s.endAt; s.version=s.version+1
 redis.call('SET',KEYS[1],cjson.encode(s))
end
if ARGV[2]=='expire' then
 if s.status=='in_progress' then return {'early'} end
 return {'ok',cjson.encode(s)}
end
if ARGV[2]=='get' or s.status~='in_progress' then return {'ok',cjson.encode(s)} end
local expected=tonumber(ARGV[3]); local payload=ARGV[4]
if s.version~=expected then
 if ARGV[2]=='progress' and s.lastProgress==payload and s.lastProgressVersion==expected then return {'ok',cjson.encode(s)} end
 return {'conflict',cjson.encode(s)}
end
local p=cjson.decode(payload); s.answers=p.answersJson; s.score=p.score; s.version=s.version+1
if ARGV[2]=='finish' then s.status='submitted'; s.submittedAt=now
else s.lastProgress=payload; s.lastProgressVersion=expected end
redis.call('SET',KEYS[1],cjson.encode(s)); return {'ok',cjson.encode(s)}
'''


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    teamName: str = Field(strict=True)

    @field_validator("teamName")
    @classmethod
    def name(cls, value: str) -> str:
        value = " ".join(unicodedata.normalize("NFKC", value).split())
        if not value or len(value) > 60 or any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("Invalid team name")
        return value


def letter(v: Any) -> bool:
    return v is None or (isinstance(v, str) and len(v) == 1 and 'А' <= v <= 'Я')


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: StrictInt = Field(ge=0)
    answers: dict
    score: StrictInt = Field(ge=0, le=20)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, a: dict) -> dict:
        if set(a) != {"task1", "task2", "task3", "task4", "task5"}:
            raise ValueError("Invalid answers")
        one, three, four = a['task1'], a['task3'], a['task4']
        if not isinstance(one, list) or len(one)>5 or not all(x is None or type(x) is int and 1<=x<=5 for x in one):
            raise ValueError("Invalid task1")
        if not letter(a['task2']) or not letter(a['task5']):
            raise ValueError("Invalid letter")
        if not isinstance(three,list) or len(three)!=4 or not all(letter(x) for x in three):
            raise ValueError("Invalid task3")
        if not isinstance(four,list) or len(four)!=4 or not all(x is None or type(x) is int and 1<=x<=10 for x in four[:3]) or not letter(four[3]):
            raise ValueError("Invalid task4")
        return a


def snapshot(s: dict, token: bool = False) -> dict:
    fields = ('sessionId', 'teamName', 'status', 'startedAt', 'endAt', 'answers', 'score', 'version')
    result = {key: s[key] for key in fields}
    result['submittedAt'] = s.get('submittedAt')
    result['answers'] = json.loads(result['answers'])
    result['serverNow'] = now_ms()
    if token:
        result['sessionToken'] = s['token']
    return result


def publish(s: dict) -> str:
    url = env('PUBLIC_BASE_URL').rstrip('/') + '/api/internal/expire'
    response = httpx.post(os.getenv('QSTASH_URL', 'https://qstash.upstash.io').rstrip('/') + '/v2/publish/' + url,
        headers={'Authorization':'Bearer '+env('QSTASH_TOKEN'), 'Upstash-Not-Before':str((s['endAt']+999)//1000), 'Upstash-Deduplication-Id':'expiry-'+s['sessionId']},
        json={'sessionId':s['sessionId']}, timeout=8)
    response.raise_for_status()
    return response.json()['messageId']


def telegram_call(method: str, payload: dict) -> None:
    try:
        response = httpx.post(
            'https://api.telegram.org/bot' + env('TELEGRAM_BOT_TOKEN') + '/' + method,
            json=payload,
            timeout=8,
        )
        response.raise_for_status()
        if not response.json().get('ok'):
            raise ValueError('Provider rejected request')
    except (httpx.HTTPError, ValueError):
        raise RuntimeError('Telegram request failed') from None


def send_telegram(chat: str, text: str, buttons: list | None = None, *, reply_markup: dict | None = None) -> None:
    payload = {'chat_id': chat, 'text': text}
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    elif buttons is not None:
        payload['reply_markup'] = {'inline_keyboard': buttons}
    telegram_call('sendMessage', payload)


CLAIM_NOTICE = '''
local raw=redis.call('GET',KEYS[1]); if not raw then return 0 end
local s=cjson.decode(raw)
if not s.ready then return 0 end
if ARGV[1]=='end' and s.status=='in_progress' then return 0 end
local id=ARGV[1]..':'..ARGV[2]
if s.notices[id] then return 0 end
s.notices[id]=true
redis.call('SET',KEYS[1],cjson.encode(s))
return 1
'''


def notify_once(s: dict, event: str) -> None:
    # Claim before sending: Telegram cannot deduplicate an ambiguous send failure.
    admin_ids = os.getenv('TELEGRAM_ADMIN_IDS', '')
    for admin in filter(None, (item.strip() for item in admin_ids.split(','))):
        try:
            if not redis('SISMEMBER', 'game:telegram:subscribers', admin):
                continue
            if eval_script(CLAIM_NOTICE, ['game:session:' + s['sessionId']], [event, admin]):
                text = (f"🔎 Команда «{s['teamName']}» начала расследование." if event == 'start' else f"🏁 Команда «{s['teamName']}» прошла квест.\n\n🏆 Баллы: {s['score']}/20.")
                send_telegram(admin, text)
        except Exception:
            logging.getLogger(__name__).warning('Telegram notification failed')
            continue


def transition(session_id: str, token_hash: str, action: str, mutation: Mutation | None = None) -> dict:
    payload = ''
    if mutation:
        answers_json = json.dumps(mutation.answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        payload = json.dumps(
            {'answersJson': answers_json, 'score': mutation.score},
            ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        )
    result = eval_script(
        TRANSITION,
        ['game:session:' + session_id],
        [token_hash, action, mutation.version if mutation else '', payload],
    )
    code = result[0]
    errors = {'missing': (404, 'Not found'), 'unauthorized': (401, 'Unauthorized'),
              'pending': (503, 'Registration pending'), 'early': (503, 'Too early')}
    if code in errors:
        status, detail = errors[code]
        raise HTTPException(status, detail)
    session = json.loads(result[1])
    if session['status'] != 'in_progress':
        notify_once(session, 'end')
    if code == 'conflict':
        raise HTTPException(409, detail={'code': 'version_conflict', 'session': snapshot(session)})
    return session


def bearer(value: str | None) -> str:
    if not value or not value.startswith('Bearer ') or not value[7:]:
        raise HTTPException(401, 'Unauthorized')
    return digest(value[7:])


@app.exception_handler(Exception)
async def unavailable(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={'detail':'Service temporarily unavailable'})


@app.post('/api/sessions')
def register(body: Registration, idempotency_key: str = Header(alias='Idempotency-Key', min_length=16, max_length=200)):
    session_id = secrets.token_urlsafe(24)
    token = secrets.token_urlsafe(32)
    name_key = 'game:name:' + digest(body.teamName.casefold())
    idem_key = 'game:idem:' + digest(idempotency_key)
    session = {
        'sessionId': session_id, 'token': token, 'tokenHash': digest(token),
        'teamName': body.teamName, 'nameKey': name_key, 'idemKey': idem_key,
        'notices': {}, 'status': 'in_progress', 'submittedAt': None,
        'answers': json.dumps(EMPTY, ensure_ascii=False, separators=(',', ':')),
        'score': 0, 'version': 0, 'ready': False,
    }
    result = eval_script(
        RESERVE, [idem_key, name_key, 'game:session:' + session_id],
        [json.dumps(session, ensure_ascii=False)],
    )
    if result[0] == 'taken':
        raise HTTPException(409, detail={'code': 'name_taken'})
    if result[0] == 'deleted':
        raise HTTPException(404, 'Not found')
    session_id = result[1]
    session = json.loads(result[2])
    if session['teamName'].casefold() != body.teamName.casefold():
        raise HTTPException(409, detail={'code': 'idempotency_key_reused'})
    if not session['ready']:
        message_id = publish(session)
        raw = eval_script(MARK_READY, ['game:session:' + session_id], [message_id])
        if not raw:
            raise HTTPException(503, 'Registration expired')
        session = json.loads(raw)
    notify_once(session, 'start')
    session = transition(session_id, session['tokenHash'], 'get')
    return JSONResponse(status_code=201 if result[0] == 'created' else 200, content=snapshot(session, True))


@app.get('/api/sessions/{session_id}')
def get_session(session_id: str, authorization: str | None = Header(default=None)):
    return snapshot(transition(session_id,bearer(authorization),'get'))


@app.put('/api/sessions/{session_id}/progress')
def progress(session_id: str, body: Mutation, authorization: str | None = Header(default=None)):
    return snapshot(transition(session_id,bearer(authorization),'progress',body))


@app.post('/api/sessions/{session_id}/finish')
def finish(session_id: str, body: Mutation, authorization: str | None = Header(default=None)):
    session = transition(session_id, bearer(authorization), 'finish', body)
    if session['status'] == 'submitted':
        cancel_message(session.get('messageId'))
    return snapshot(session)


@app.post('/api/internal/expire')
async def expire(request: Request, upstash_signature: str | None = Header(default=None)):
    import jwt
    raw=await request.body()
    if not upstash_signature: raise HTTPException(401,'Unauthorized')
    verified=False
    for key in (env('QSTASH_CURRENT_SIGNING_KEY'), env('QSTASH_NEXT_SIGNING_KEY')):
        try:
            claims=jwt.decode(upstash_signature,key,algorithms=['HS256'],issuer='Upstash',
                subject=env('PUBLIC_BASE_URL').rstrip('/')+'/api/internal/expire',
                options={'require':['iss','sub','exp','nbf','iat','body']})
            expected=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
            if hmac.compare_digest(claims['body'].rstrip('='),expected):
                verified=True
                break
        except (jwt.PyJWTError, TypeError, AttributeError):
            continue
    if not verified: raise HTTPException(401,'Unauthorized')
    try:
        data=json.loads(raw); sid=data['sessionId']
        if not isinstance(sid,str) or not sid or len(sid)>100: raise ValueError()
    except (ValueError, KeyError, TypeError): raise HTTPException(400,'Invalid body')
    try: await run_in_threadpool(transition,sid,'','expire')
    except HTTPException as exc:
        if exc.status_code!=404: raise
    return {'ok':True}


def cancel_message(message_id: str | None) -> None:
    if not message_id: return
    try:
        httpx.delete(os.getenv('QSTASH_URL', 'https://qstash.upstash.io').rstrip('/')+'/v2/messages/'+message_id, headers={'Authorization':'Bearer '+env('QSTASH_TOKEN')},timeout=8).raise_for_status()
    except Exception:
        pass


CONFIRM_DELETE = '''
local expected=redis.call('GET',KEYS[1])
if expected~=ARGV[1] then return nil end
redis.call('DEL',KEYS[1])
local raw=redis.call('GET',KEYS[2]); if not raw then return nil end
local s=cjson.decode(raw)
redis.call('DEL',KEYS[2])
if redis.call('GET',s.nameKey)==s.sessionId then redis.call('DEL',s.nameKey) end
redis.call('ZREM','game:teams',s.sessionId)
redis.call('EXPIRE',s.idemKey,86400)
return raw
'''


def answer_callback(callback_id: str) -> None:
    try:
        telegram_call('answerCallbackQuery', {'callback_query_id': callback_id})
    except RuntimeError:
        logging.getLogger(__name__).warning('Telegram callback acknowledgement failed')


def team_page(chat_id: str, page: int, deletion: bool = False) -> None:
    page = max(1, min(page, 100000))
    page_size = 10 if deletion else 5
    ids = redis('ZREVRANGE', 'game:teams', (page - 1) * page_size, page * page_size)
    displayed = 0
    buttons = []
    for session_id in ids[:page_size]:
        if deletion:
            raw = redis('GET', 'game:session:' + session_id)
            session = json.loads(raw) if raw else None
            if session and session.get('ready'):
                buttons.append([{'text': session['teamName'], 'callback_data': 'select:' + session_id}])
            continue
        try:
            session = transition(session_id, '', 'get')
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        status = 'Активна' if session['status'] == 'in_progress' else 'Завершена'
        started = datetime.fromtimestamp(session['startedAt'] / 1000, timezone(timedelta(hours=3)))
        text = f"👥 Команда: {session['teamName']}\n📊 Статус: {status}\n⏱ Начало: {started:%d.%m.%Y %H:%M} (МСК)"
        if session['status'] != 'in_progress':
            text += f"\n🏆 Результат: {session['score']}/20"
        if displayed:
            time.sleep(1)
        send_telegram(chat_id, text, [[{'text': '🗑 Удалить', 'callback_data': 'team:' + session_id}]])
        displayed += 1
    navigation = []
    if page > 1:
        navigation.append({'text': '←', 'callback_data': f"{'d' if deletion else 't'}page:{page-1}"})
    if len(ids) > page_size:
        navigation.append({'text': '→', 'callback_data': f"{'d' if deletion else 't'}page:{page+1}"})
    if deletion:
        if navigation:
            buttons.append(navigation)
        send_telegram(chat_id, 'Выберите команду для удаления:' if buttons else '📭 Команд пока нет', buttons or None)
        return
    if navigation:
        if displayed:
            time.sleep(1)
        send_telegram(chat_id, f'Страница {page}', [navigation])
    elif not displayed:
        send_telegram(chat_id, '📭 Команд пока нет')


def clear_team_button(chat_id: str, message_id: str) -> None:
    if message_id.isdigit():
        try:
            telegram_call('editMessageReplyMarkup', {'chat_id': chat_id, 'message_id': int(message_id), 'reply_markup': {'inline_keyboard': []}})
        except RuntimeError:
            logging.getLogger(__name__).warning('Telegram button removal failed')


def send_delete_confirmation(chat_id: str, team_name: str, nonce: str) -> None:
    buttons = [
        [{'text': '✅ Подтвердить', 'callback_data': 'confirm:' + nonce}],
        [{'text': '❌ Отмена', 'callback_data': 'cancel:' + nonce}],
    ]
    send_telegram(chat_id, f"Удалить команду «{team_name}»?", buttons)


def handle_telegram_callback(callback: dict, chat_id: str, sender_id: str) -> None:
    value = callback.get('data', '')
    if not isinstance(value, str):
        return
    if value.startswith(('dpage:', 'tpage:')):
        try:
            page = int(value.split(':', 1)[1])
        except ValueError:
            return
        team_page(chat_id, page, value.startswith('dpage:'))
    elif value.startswith(('team:', 'select:')):
        session_id = value.split(':', 1)[1]
        message_id = callback.get('message', {}).get('message_id')
        source = str(message_id) if value.startswith('team:') and type(message_id) is int else ''
        raw = redis('GET', 'game:session:' + session_id)
        session = json.loads(raw) if raw else None
        if not session or not session.get('ready'):
            clear_team_button(chat_id, source)
            send_telegram(chat_id, 'Команда уже удалена.')
            return
        nonce = secrets.token_urlsafe(16)
        redis('SET', 'game:confirm:' + nonce, sender_id + ':' + session_id + ':' + source, 'EX', 300)
        team_name = session['teamName']
        if value.startswith('select:'):
            send_telegram(chat_id, f'Команда «{team_name}»', [[{'text': 'Удалить', 'callback_data': 'delete:' + nonce}], [{'text': 'Отмена', 'callback_data': 'cancel:' + nonce}]])
        else:
            send_delete_confirmation(chat_id, team_name, nonce)
    elif value.startswith('delete:'):
        # Old messages may still contain the previous two-step delete button.
        nonce = value[7:]
        saved = redis('GET', 'game:confirm:' + nonce)
        if not saved or not saved.startswith(sender_id + ':'):
            send_telegram(chat_id, 'Подтверждение истекло или команда уже удалена.')
            return
        session_id = saved.split(':', 2)[1]
        raw = redis('GET', 'game:session:' + session_id)
        if not raw:
            send_telegram(chat_id, 'Команда уже удалена.')
            return
        send_delete_confirmation(chat_id, json.loads(raw)['teamName'], nonce)
    elif value.startswith('cancel:'):
        nonce = value[7:]
        saved = redis('GET', 'game:confirm:' + nonce)
        if saved and saved.startswith(sender_id + ':') and redis('DEL', 'game:confirm:' + nonce):
            send_telegram(chat_id, 'Удаление отменено.')
        else:
            send_telegram(chat_id, 'Подтверждение истекло или уже обработано.')
    elif value.startswith('confirm:'):
        nonce = value[8:]
        saved = redis('GET', 'game:confirm:' + nonce)
        if not saved or not saved.startswith(sender_id + ':'):
            send_telegram(chat_id, 'Подтверждение истекло или команда уже удалена.')
            return
        parts = saved.split(':', 2)
        session_id = parts[1]
        raw = eval_script(CONFIRM_DELETE, ['game:confirm:' + nonce, 'game:session:' + session_id], [saved])
        if raw:
            session = json.loads(raw)
            if len(parts) > 2:
                clear_team_button(chat_id, parts[2])
            cancel_message(session.get('messageId'))
            send_telegram(chat_id, f"✅ Команда „{session['teamName']}“ удалена")
        else:
            if not redis('GET', 'game:session:' + session_id):
                if len(parts) > 2:
                    clear_team_button(chat_id, parts[2])
                send_telegram(chat_id, 'Команда уже удалена.')
            else:
                send_telegram(chat_id, 'Подтверждение истекло или уже обработано.')


TEAM_LIST_BUTTON = '📋 Список команд'
START_READY = ('🟢 Artcode Detective — сервис работает\n\n'
               '✅ Telegram → Backend: соединение установлено\n\n'
               '✅ Backend → Redis: соединение установлено\n\n'
               '🤖 Бот готов к работе.\n\n'
               'Используй кнопку «📋 Список команд» для управления игровыми сессиями.')
START_UNAVAILABLE = ('🟡 Artcode Detective — частичная недоступность\n\n'
                     '✅ Telegram → Backend: соединение установлено\n\n'
                     '❌ Backend → Redis: соединение отсутствует\n\n'
                     '⚠️ Управление командами временно недоступно.')


def handle_telegram(data: dict) -> None:
    update_id = data.get('update_id')
    if type(update_id) is not int:
        return
    callback = data.get('callback_query')
    message = callback.get('message', {}) if isinstance(callback, dict) else data.get('message', {})
    if not isinstance(message, dict):
        return
    sender = callback.get('from', {}) if isinstance(callback, dict) else message.get('from', {})
    chat = message.get('chat', {})
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return
    if type(chat.get('id')) is not int or type(sender.get('id')) is not int:
        return
    chat_id, sender_id = str(chat['id']), str(sender['id'])
    if chat.get('type') != 'private' or chat_id != sender_id:
        return
    text = message.get('text', '')
    parts = text.split() if isinstance(text, str) else []
    command = parts[0].split('@', 1)[0].lower() if parts else ''
    allowed = {item.strip() for item in os.getenv('TELEGRAM_ADMIN_IDS', '').split(',') if item.strip()}
    if sender_id not in allowed:
        if not isinstance(callback, dict) and command == '/start':
            send_telegram(chat_id, 'Доступ запрещён.')
        return
    if isinstance(callback, dict):
        callback_id = callback.get('id')
        if not isinstance(callback_id, str):
            return
        answer_callback(callback_id)
    if command == '/start' and not isinstance(callback, dict):
        try:
            if redis('PING') != 'PONG':
                raise RuntimeError('Redis ping failed')
            redis('SADD', 'game:telegram:subscribers', sender_id)
            fresh = redis('SET', 'game:telegram:update:' + str(update_id), '1', 'EX', 86400, 'NX')
        except (httpx.HTTPError, RuntimeError, ValueError):
            send_telegram(chat_id, START_UNAVAILABLE)
            return
        if fresh:
            try:
                send_telegram(chat_id, START_READY, reply_markup={
                    'keyboard': [[{'text': TEAM_LIST_BUTTON}]],
                    'resize_keyboard': True,
                    'is_persistent': True,
                })
            except Exception:
                # A webhook retry can resend when Telegram rejects or times out.
                try:
                    redis('DEL', 'game:telegram:update:' + str(update_id))
                except (httpx.HTTPError, RuntimeError, ValueError):
                    logging.getLogger(__name__).warning('Telegram update claim cleanup failed')
                raise
        return
    if not redis('SET', 'game:telegram:update:' + str(update_id), '1', 'EX', 86400, 'NX'):
        return
    if isinstance(callback, dict):
        handle_telegram_callback(callback, chat_id, sender_id)
    elif text == TEAM_LIST_BUTTON or command == '/teams':
        team_page(chat_id, 1)
    elif command == '/delete':
        team_page(chat_id, 1, True)


@app.post('/api/webhooks/telegram')
async def telegram(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(x_telegram_bot_api_secret_token, env('TELEGRAM_WEBHOOK_SECRET')):
        raise HTTPException(401, 'Unauthorized')
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(400, 'Invalid body')
    if isinstance(data, dict):
        await run_in_threadpool(handle_telegram, data)
    return {'ok': True}


# API routes must be declared before the public frontend mount.
app.mount('/', StaticFiles(directory='frontend', html=True), name='frontend')

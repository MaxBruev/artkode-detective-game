import base64
import hashlib
import json
import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import jwt
from fastapi import HTTPException
from pydantic import ValidationError
from backend import main as api

CONFIG={'QSTASH_CURRENT_SIGNING_KEY':'current-secret-for-testing-at-least-32-bytes','QSTASH_NEXT_SIGNING_KEY':'next-secret-for-testing-at-least-32-bytes','PUBLIC_BASE_URL':'https://example.com','TELEGRAM_WEBHOOK_SECRET':'webhook-secret','TELEGRAM_ADMIN_IDS':'123'}

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,CONFIG)
        self.env.start()


    def tearDown(self): self.env.stop()

    def signature(self, body, key='current-secret-for-testing-at-least-32-bytes', subject='https://example.com/api/internal/expire'):
        now=int(time.time())
        return jwt.encode({'iss':'Upstash','sub':subject,'iat':now,'nbf':now-1,'exp':now+60,'body':base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode()},key,algorithm='HS256')

    def test_expiry_signature_checks_body_subject_and_both_keys(self):
        body=b'{"sessionId":"abc"}'
        class Request:
            async def body(self): return body
        def call(signature):
            coroutine=api.expire(Request(),signature)
            try: coroutine.send(None)
            except StopIteration as result: return result.value
        async def immediate(function, *args): return function(*args)
        with patch.object(api,'transition') as transition, patch.object(api,'run_in_threadpool',immediate):
            for key in ('current-secret-for-testing-at-least-32-bytes','next-secret-for-testing-at-least-32-bytes'):
                self.assertEqual(call(self.signature(body,key)),{'ok':True})
            for signature in (self.signature(b'other'),self.signature(body,subject='https://evil.example/'),self.signature(body,key='incorrect-signing-key-at-least-32-bytes')):
                with self.assertRaises(HTTPException) as err: call(signature)
                self.assertEqual(err.exception.status_code,401)
            self.assertEqual(transition.call_count,2)

    def test_answer_validation_and_auth(self):
        with self.assertRaises(HTTPException): api.bearer(None)
        for task, value in [('task1',[True]),('task2','['),('task3',[None]),('task4',[11,None,None,None])]:
            answers=dict(api.EMPTY); answers[task]=value
            with self.assertRaises(ValidationError): api.Mutation(version=0,answers=answers,score=0)

    def test_telegram_private_allowlist_secret_and_dedupe(self):
        seen=set(); sent=[]
        def redis(*args):
            if args[0]=='PING': return 'PONG'
            if args[0]=='SET':
                if args[1] in seen: return None
                seen.add(args[1]); return 'OK'
        update={'update_id':42,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'text':'/start'}}
        class Request:
            async def json(self): return update
        async def immediate(function, *args): return function(*args)
        def call(secret):
            coroutine=api.telegram(Request(),secret)
            try: coroutine.send(None)
            except StopIteration as result: return result.value
        with patch.object(api,'redis',side_effect=redis), patch.object(api,'send_telegram',side_effect=lambda *x, **kw:sent.append((x, kw))), patch.object(api,'run_in_threadpool',immediate):
            with self.assertRaises(HTTPException): call(None)
            update['message']['chat']['type']='group'
            call('webhook-secret')
            update['message']['chat']['type']='private'
            call('webhook-secret')
            call('webhook-secret')
            self.assertEqual(len(sent),1)

    def test_start_health_and_authorization(self):
        update = {'update_id': 1, 'message': {'chat': {'id': 123, 'type': 'private'},
                  'from': {'id': 123}, 'text': '/start'}}
        seen, subscribers, commands = set(), set(), []
        def redis(*args):
            commands.append(args)
            if args[0] == 'PING': return 'PONG'
            if args[0] == 'SADD': subscribers.add(args[2]); return 1
            if args[0] == 'SET':
                if args[1] in seen: return None
                seen.add(args[1]); return 'OK'
            raise AssertionError(args)
        with patch.object(api, 'redis', side_effect=redis), patch.object(api, 'send_telegram') as send:
            api.handle_telegram(update)
            api.handle_telegram(update)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(subscribers, {'123'})
            self.assertEqual(send.call_args.args[1], '🟢 Artcode Detective — сервис работает\n\n✅ Telegram → Backend: соединение установлено\n\n✅ Backend → Redis: соединение установлено\n\n🤖 Бот готов к работе.\n\nИспользуй кнопку «📋 Список команд» для управления игровыми сессиями.')
            self.assertEqual(send.call_args.kwargs['reply_markup'], {'keyboard': [[{'text': '📋 Список команд'}, {'text': '🏆 Общий рейтинг'}]], 'resize_keyboard': True, 'is_persistent': True})
            self.assertTrue(all(c[0] in ('PING', 'SADD', 'SET') for c in commands))
            update['update_id'] = 2
            api.handle_telegram(update)
            self.assertEqual(send.call_count, 2)
            self.assertEqual(sum(c[0] == 'PING' for c in commands), 3)

        update['update_id'] = 3
        with patch.object(api, 'redis', side_effect=RuntimeError('offline')), patch.object(api, 'send_telegram') as send:
            api.handle_telegram(update)
            self.assertEqual(send.call_args.args[1], '🟡 Artcode Detective — частичная недоступность\n\n✅ Telegram → Backend: соединение установлено\n\n❌ Backend → Redis: соединение отсутствует\n\n⚠️ Управление командами временно недоступно.')
            update['message']['chat']['id'] = update['message']['from']['id'] = 456
            api.handle_telegram(update)
            self.assertEqual(send.call_args.args, ('456', 'Доступ запрещён.'))

        update['message']['chat']['id'] = update['message']['from']['id'] = 123
        for failed in ('SADD', 'SET'):
            def failing_redis(*args):
                if args[0] == failed: raise RuntimeError('offline')
                return 'PONG' if args[0] == 'PING' else 1
            with patch.object(api, 'redis', side_effect=failing_redis), patch.object(api, 'send_telegram') as send:
                api.handle_telegram(update)
                self.assertEqual(send.call_args.args[1], api.START_UNAVAILABLE)

    def test_team_list_button_routes_to_first_page(self):
        update = {'update_id': 10, 'message': {'chat': {'id': 123, 'type': 'private'},
                  'from': {'id': 123}, 'text': '📋 Список команд'}}
        with patch.object(api, 'redis', return_value='OK'), patch.object(api, 'team_page') as page:
            api.handle_telegram(update)
            page.assert_called_once_with('123', 1)

    def test_leaderboard_button_and_ordering(self):
        update = {'update_id': 10, 'message': {'chat': {'id': 123, 'type': 'private'},
                  'from': {'id': 123}, 'text': '🏆 Общий рейтинг'}}
        records = [
            ('a', {'teamName': 'Поздняя', 'status': 'submitted', 'score': 20, 'submittedAt': 200, 'ready': True}),
            ('b', {'teamName': '<Ранняя & команда>', 'status': 'timed_out', 'score': 20, 'submittedAt': 100, 'ready': True}),
            ('c', {'teamName': 'Без времени Б', 'status': 'submitted', 'score': 20, 'ready': True}),
            ('d', {'teamName': 'Без времени А', 'status': 'submitted', 'score': 20, 'submittedAt': None, 'ready': True}),
            ('e', {'teamName': 'Активная', 'status': 'in_progress', 'score': 20, 'ready': True}),
            ('f', {'teamName': 'Без баллов', 'status': 'submitted', 'ready': True}),
            ('g', {'teamName': 'Низкий', 'status': 'submitted', 'score': 0, 'submittedAt': 1, 'ready': True}),
        ]
        batch = [json.dumps({'id': sid, **session}) if session.get('status') in ('submitted', 'timed_out') and 'score' in session else ''
                 for sid, session in records]
        with patch.object(api, 'redis', return_value='OK'), patch.object(api, 'eval_script', return_value=['0', batch]), \
             patch.object(api, 'send_telegram') as send, patch.object(api, 'transition') as transition, \
             patch.object(api, 'notify_once') as notify:
            api.handle_telegram(update)
            text = send.call_args.args[1]
            self.assertEqual(text.splitlines(), ['🏆 ОБЩИЙ РЕЙТИНГ', '', '🥇 1. <Ранняя & команда> — 20/20',
                '🥈 2. Поздняя — 20/20', '🥉 3. Без времени А — 20/20',
                '4. Без времени Б — 20/20', '5. Низкий — 0/20'])
            transition.assert_not_called()
            notify.assert_not_called()

    def test_leaderboard_empty_and_batched_message_splitting(self):
        with patch.object(api, 'eval_script', return_value=['0', []]), patch.object(api, 'send_telegram') as send:
            api.leaderboard('123')
            self.assertEqual(send.call_args.args[1], '🏆 Рейтинг пока пуст. Ни одна команда ещё не завершила расследование')

        records = [json.dumps({'id': str(i), 'teamName': f'{i:03d}' + '😀' * 50,
                    'score': 1, 'submittedAt': i}) for i in range(110)]
        with patch.object(api, 'eval_script', side_effect=[['1', records[:100]], ['2', []],
                                                           ['0', records[99:]]]) as read, \
             patch.object(api, 'send_telegram') as send, patch.object(api.time, 'sleep'):
            api.leaderboard('123')
            messages = [call.args[1] for call in send.call_args_list]
            self.assertTrue(all(len(message.encode('utf-16-le')) // 2 <= 4096 for message in messages))
            rows = '\n'.join(messages).splitlines()[2:]
            self.assertEqual(len(rows), 110)
            self.assertTrue(rows[-1].startswith('110. '))
            self.assertEqual(read.call_count, 3)
            self.assertEqual([call.args[2][0] for call in read.call_args_list], ['0', '1', '2'])

    def test_redis_ping_uses_upstash_command_and_result(self):
        response = unittest.mock.Mock()
        response.json.return_value = {'result': 'PONG'}
        with patch.dict(os.environ, {'UPSTASH_REDIS_REST_URL': 'https://redis.example', 'UPSTASH_REDIS_REST_TOKEN': 'token'}), \
             patch.object(api.httpx, 'post', return_value=response) as post:
            self.assertEqual(api.redis('PING'), 'PONG')
            self.assertEqual(post.call_args.kwargs['json'], ['PING'])

            for malformed in ([], {}, 'PONG'):
                response.json.return_value = malformed
                with self.assertRaises(RuntimeError): api.redis('PING')

    def test_start_without_admins_and_retry_after_send_failure(self):
        update = {'update_id': 12, 'message': {'chat': {'id': 123, 'type': 'private'},
                  'from': {'id': 123}, 'text': '/start'}}
        for config in ({'TELEGRAM_ADMIN_IDS': ''}, {}):
            with patch.dict(os.environ, config, clear=True), patch.object(api, 'redis') as redis, \
                 patch.object(api, 'send_telegram') as send:
                api.handle_telegram(update)
                send.assert_called_once_with('123', 'Доступ запрещён.')
                redis.assert_not_called()
        seen = set()
        def redis(*args):
            if args[0] == 'PING': return 'PONG'
            if args[0] == 'SADD': return 1
            if args[0] == 'DEL': seen.discard(args[1]); return 1
            if args[0] == 'SET':
                if args[1] in seen: return None
                seen.add(args[1]); return 'OK'
            raise AssertionError(args)
        with patch.object(api, 'redis', side_effect=redis), \
             patch.object(api, 'send_telegram', side_effect=[RuntimeError('Telegram failed'), None]) as send:
            with self.assertRaises(RuntimeError): api.handle_telegram(update)
            api.handle_telegram(update)
            self.assertEqual(send.call_count, 2)

    def test_callback_acknowledged_before_redis_failure(self):
        update = {'update_id': 11, 'callback_query': {'id': 'query', 'from': {'id': 123},
                  'message': {'chat': {'id': 123, 'type': 'private'}}, 'data': 'tpage:1'}}
        with patch.object(api, 'answer_callback') as answer, patch.object(api, 'redis', side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError): api.handle_telegram(update)
            answer.assert_called_once_with('query')

    def test_terminal_and_conflict_snapshots(self):
        answers = json.dumps(api.EMPTY)
        session = {'sessionId': 'one', 'teamName': 'Команда', 'status': 'in_progress',
                   'startedAt': 100, 'endAt': 200, 'submittedAt': None, 'answers': answers,
                   'score': 0, 'version': 3}
        mutation = api.Mutation(version=2, answers=api.EMPTY, score=0)
        with patch.object(api, 'eval_script', return_value=['conflict', json.dumps(session)]), patch.object(api, 'notify_once'):
            with self.assertRaises(HTTPException) as error:
                api.transition('one', 'token-hash', 'progress', mutation)
            self.assertEqual(error.exception.detail['session']['version'], 3)
            self.assertEqual(error.exception.detail['code'], 'version_conflict')
        for status in ('submitted', 'timed_out'):
            session['status'] = status
            session['submittedAt'] = 200
            with patch.object(api, 'eval_script', return_value=['ok', json.dumps(session)]), patch.object(api, 'notify_once') as notify:
                result = api.transition('one', 'token-hash', 'finish', mutation)
                self.assertEqual(result['status'], status)
                notify.assert_called_once()

    def test_admin_selection_confirm_and_cancel(self):
        saved = {}
        messages = []
        sessions = {
            'first': {'ready': True, 'teamName': 'Первая', 'status': 'in_progress',
                      'startedAt': 0, 'messageId': 'expiry-first'},
            'second': {'ready': True, 'teamName': 'Вторая', 'status': 'submitted',
                       'startedAt': 0, 'score': 12},
        }
        def redis(*args):
            if args[0] == 'SET':
                if args[1].startswith('game:telegram:update:') and args[1] in saved: return None
                saved[args[1]] = args[2]
                return 'OK'
            if args[0] == 'GET':
                if args[1].startswith('game:session:'):
                    value = sessions.get(args[1].split(':')[-1])
                    return json.dumps(value) if value else None
                return saved.get(args[1])
            if args[0] == 'DEL':
                return int(saved.pop(args[1], None) is not None)
            if args[0] == 'ZREVRANGE': return list(sessions)
        def evaluate(script, keys, args):
            self.assertEqual(script, api.CONFIRM_DELETE)
            if saved.get(keys[0]) != args[0]: return None
            saved.pop(keys[0])
            name = keys[1].split(':')[-1]
            session = sessions.pop(name, None)
            return json.dumps(session) if session else None
        def update(number, value):
            return {'update_id': number, 'callback_query': {'id': str(number), 'from': {'id': 123},
                    'message': {'chat': {'id': 123, 'type': 'private'}, 'message_id': 77}, 'data': value}}
        with patch.object(api, 'redis', side_effect=redis), patch.object(api, 'eval_script', side_effect=evaluate), \
             patch.object(api, 'send_telegram', side_effect=lambda *args: messages.append(args)), \
             patch.object(api, 'answer_callback'), patch.object(api, 'cancel_message') as cancel_message, \
             patch.object(api, 'telegram_call') as telegram_call, patch.object(api.time, 'sleep'), \
             patch.object(api, 'transition', side_effect=lambda sid, *_: sessions[sid]):
            api.handle_telegram({'update_id': 1, 'message': {'chat': {'id': 123, 'type': 'private'}, 'from': {'id': 123}, 'text': '/delete'}})
            self.assertEqual([row[0]['callback_data'] for row in messages[-1][2]], ['select:first', 'select:second'])
            messages.clear()
            api.handle_telegram({'update_id': 3, 'message': {'chat': {'id': 123, 'type': 'private'}, 'from': {'id': 123}, 'text': '/teams'}})
            self.assertEqual(len(messages), 2)
            self.assertTrue(messages[0][1].startswith('👥 Команда: Первая\n📊 Статус: Активна\n⏱ Начало:'))
            self.assertIn('01.01.1970 03:00 (МСК)', messages[0][1])
            self.assertIn('📊 Статус: Завершена', messages[1][1])
            self.assertIn('🏆 Результат: 12/20', messages[1][1])
            first_button = messages[0][2][0][0]
            second_button = messages[1][2][0][0]
            self.assertEqual(first_button, {'text': '🗑 Удалить', 'callback_data': 'team:first'})
            self.assertEqual(second_button, {'text': '🗑 Удалить', 'callback_data': 'team:second'})
            api.handle_telegram(update(2, first_button['callback_data']))
            self.assertEqual(messages[-1][1], 'Удалить команду «Первая»?')
            nonce = messages[-1][2][0][0]['callback_data'].split(':')[1]
            api.handle_telegram(update(4, 'confirm:' + nonce))
            self.assertNotIn('first', sessions)
            self.assertIn('second', sessions)
            self.assertEqual(messages[-1][1], '✅ Команда „Первая“ удалена')
            cancel_message.assert_called_once_with('expiry-first')
            telegram_call.assert_called_once_with('deleteMessage', {'chat_id': '123', 'message_id': 77})
            sessions['replacement'] = {'ready': True, 'teamName': 'Первая'}
            api.handle_telegram(update(5, 'confirm:' + nonce))
            self.assertIn('second', sessions)
            api.handle_telegram(update(10, first_button['callback_data']))
            self.assertEqual(messages[-1][1], 'Команда уже удалена.')
            self.assertIn('replacement', sessions)
            before_cancel = len(messages)
            api.handle_telegram(update(9, 'cancel:' + nonce))
            self.assertEqual(len(messages), before_cancel)
            api.handle_telegram(update(6, 'team:second'))
            nonce = messages[-1][2][0][0]['callback_data'].split(':')[1]
            before_cancel = len(messages)
            api.handle_telegram(update(7, 'cancel:' + nonce))
            self.assertEqual(len(messages), before_cancel)
            api.handle_telegram(update(8, 'confirm:' + nonce))
            self.assertIn('second', sessions)

    def test_confirmation_cleanup_failure_and_legacy_selector(self):
        session = {'teamName': 'Первая', 'messageId': 'expiry'}
        callback = {'data': 'confirm:nonce', 'message': {'message_id': 88}}
        def telegram(method, payload):
            if method == 'deleteMessage': raise RuntimeError('too old')
        with patch.object(api, 'redis', return_value='123:first:77'), \
             patch.object(api, 'eval_script', return_value=json.dumps(session)) as evaluate, \
             patch.object(api, 'telegram_call', side_effect=telegram) as call, \
             patch.object(api, 'cancel_message') as cancel, patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            evaluate.assert_called_once()
            cancel.assert_called_once_with('expiry')
            self.assertEqual([(c.args[0], c.args[1]['message_id']) for c in call.call_args_list],
                             [('deleteMessage', 88), ('editMessageReplyMarkup', 88),
                              ('deleteMessage', 77), ('editMessageReplyMarkup', 77)])
            self.assertEqual(send.call_args.args[1], '✅ Команда „Первая“ удалена')
        with patch.object(api, 'redis', return_value='123:first:'), \
             patch.object(api, 'eval_script', return_value=json.dumps(session)), \
             patch.object(api, 'telegram_call') as call, patch.object(api, 'cancel_message'), \
             patch.object(api, 'send_telegram'):
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_called_once_with('deleteMessage', {'chat_id': '123', 'message_id': 88})

    def test_cancel_does_not_hide_failed_or_foreign_confirmation(self):
        callback = {'data': 'cancel:nonce', 'message': {'message_id': 88}}
        with patch.object(api, 'redis', side_effect=['123:first:77', 1]) as redis, \
             patch.object(api, 'telegram_call') as call, patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            self.assertEqual([c.args for c in redis.call_args_list],
                             [('GET', 'game:confirm:nonce'), ('DEL', 'game:confirm:nonce')])
            call.assert_called_once_with('deleteMessage', {'chat_id': '123', 'message_id': 88})
            send.assert_not_called()
        with patch.object(api, 'redis', return_value='456:first:77'), \
             patch.object(api, 'telegram_call') as call, \
             patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_not_called()
            send.assert_not_called()
        with patch.object(api, 'redis', return_value=None), \
             patch.object(api, 'telegram_call') as call, patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_not_called()
            send.assert_not_called()
        with patch.object(api, 'redis', side_effect=['123:first:77', 0]), \
             patch.object(api, 'telegram_call') as call, patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_not_called()
            send.assert_not_called()
        with patch.object(api, 'redis', side_effect=['123:first:77', RuntimeError('offline')]), \
             patch.object(api, 'telegram_call') as call:
            with self.assertRaises(RuntimeError):
                api.handle_telegram_callback(callback, '123', '123')
            call.assert_not_called()

    def test_team_page_empty_and_pagination(self):
        sent = []
        with patch.object(api, 'send_telegram', side_effect=lambda *args: sent.append(args)), \
             patch.object(api, 'redis', return_value=[]):
            api.team_page('123', 1)
        self.assertEqual(sent[-1][1], '📭 Команд пока нет')
        sent.clear()
        with patch.object(api, 'send_telegram', side_effect=lambda *args: sent.append(args)), \
             patch.object(api, 'redis', return_value=['stale'] * 6), \
             patch.object(api, 'transition', side_effect=HTTPException(404)):
            api.team_page('123', 1)
        self.assertEqual(sent[-1][2][0][0]['callback_data'], 'tpage:2')

    def test_stale_card_and_concurrent_confirm_clear_only_card(self):
        callback = {'data': 'team:gone', 'message': {'message_id': 77}}
        with patch.object(api, 'redis', return_value=None), patch.object(api, 'telegram_call') as call, \
             patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_called_once_with('editMessageReplyMarkup', {'chat_id': '123', 'message_id': 77, 'reply_markup': {'inline_keyboard': []}})
            self.assertEqual(send.call_args.args[1], 'Команда уже удалена.')
        callback['data'] = 'confirm:nonce'
        with patch.object(api, 'redis', side_effect=lambda *args: '123:gone:77' if args[1] == 'game:confirm:nonce' else None), patch.object(api, 'eval_script', return_value=None), \
             patch.object(api, 'telegram_call') as call, patch.object(api, 'send_telegram') as send:
            api.handle_telegram_callback(callback, '123', '123')
            call.assert_called_once()
            self.assertEqual(send.call_args.args[1], 'Команда уже удалена.')

    def test_duplicate_registration_retries_same_reservation_after_publish_failure(self):
        lock=threading.Lock(); data={}; idems={}; names={}; calls=[]
        def evaluate(script,keys,args):
            with lock:
                if script==api.RESERVE:
                    if keys[0] in idems: return ['existing',idems[keys[0]],json.dumps(data['game:session:'+idems[keys[0]]])]
                    if keys[1] in names: return ['taken']
                    s=json.loads(args[0]); s.update(startedAt=1,endAt=900001)
                    idems[keys[0]]=s['sessionId']; names[keys[1]]=s['sessionId']; data[keys[2]]=s
                    return ['created',s['sessionId'],json.dumps(s)]
                if script==api.MARK_READY:
                    s=data[keys[0]]; s['ready']=True; s['messageId']=args[0]; return json.dumps(s)
                raise AssertionError('unexpected script')
        def redis(*args):
            if args[0]=='GET':
                with lock: return json.dumps(data[args[1]]) if args[1] in data else None
        def publish(s):
            calls.append(s['sessionId'])
            if len(calls)==1: raise RuntimeError('ambiguous publish')
            return 'same-message'
        with patch.object(api,'eval_script',side_effect=evaluate),patch.object(api,'redis',side_effect=redis),patch.object(api,'publish',side_effect=publish),patch.object(api,'notify_once'),patch.object(api,'transition',side_effect=lambda sid, token, action: data['game:session:'+sid]):
            headers={'Idempotency-Key':'a-unique-key-long-enough'}
            with self.assertRaises(RuntimeError): api.register(api.Registration(teamName=' Team  One '),headers['Idempotency-Key'])
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda _:api.register(api.Registration(teamName='team one'),headers['Idempotency-Key']),range(4)))
            self.assertTrue(all(r.status_code==200 for r in results))
            self.assertEqual(len({json.loads(r.body)['sessionId'] for r in results}),1)
            self.assertEqual(len(set(calls)),1)
            with self.assertRaises(HTTPException) as duplicate: api.register(api.Registration(teamName='TEAM ONE'),'different-key-long-enough')
            self.assertEqual(duplicate.exception.status_code,409)

if __name__=='__main__': unittest.main()

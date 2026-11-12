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
        with patch.object(api,'redis',side_effect=redis), patch.object(api,'send_telegram',side_effect=lambda *x:sent.append(x)), patch.object(api,'run_in_threadpool',immediate):
            with self.assertRaises(HTTPException): call(None)
            update['message']['chat']['type']='group'
            call('webhook-secret')
            update['message']['chat']['type']='private'
            call('webhook-secret')
            call('webhook-secret')
            self.assertEqual(len(sent),1)

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
        sessions = {'first': {'ready': True, 'teamName': 'Первая'}, 'second': {'ready': True, 'teamName': 'Вторая'}}
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
                saved.pop(args[1], None)
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
                    'message': {'chat': {'id': 123, 'type': 'private'}}, 'data': value}}
        with patch.object(api, 'redis', side_effect=redis), patch.object(api, 'eval_script', side_effect=evaluate), \
             patch.object(api, 'send_telegram', side_effect=lambda *args: messages.append(args)), \
             patch.object(api, 'answer_callback'), patch.object(api, 'cancel_message'):
            api.handle_telegram({'update_id': 1, 'message': {'chat': {'id': 123, 'type': 'private'}, 'from': {'id': 123}, 'text': '/delete'}})
            self.assertEqual(len(messages[-1][2]), 2)
            api.handle_telegram(update(2, 'select:first'))
            nonce = messages[-1][2][0][0]['callback_data'].split(':')[1]
            api.handle_telegram(update(3, 'delete:' + nonce))
            api.handle_telegram(update(4, 'confirm:' + nonce))
            self.assertNotIn('first', sessions)
            self.assertIn('second', sessions)
            api.handle_telegram(update(5, 'confirm:' + nonce))
            self.assertIn('second', sessions)
            api.handle_telegram(update(6, 'select:second'))
            nonce = messages[-1][2][0][0]['callback_data'].split(':')[1]
            api.handle_telegram(update(7, 'cancel:' + nonce))
            api.handle_telegram(update(8, 'confirm:' + nonce))
            self.assertIn('second', sessions)

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

import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import HTTPException
from backend import main as api


class MemoryStore:
    """Model the Redis boundary for endpoint orchestration; this does not execute Lua."""
    def __init__(self):
        self.lock = threading.RLock()
        self.sessions = {}
        self.idempotency = {}
        self.names = {}
        self.now = 1000

    def eval(self, script, keys, args):
        with self.lock:
            if script == api.RESERVE:
                if keys[0] in self.idempotency:
                    sid = self.idempotency[keys[0]]
                    if sid not in self.sessions:
                        return ['deleted']
                    return ['existing', sid, json.dumps(self.sessions[sid])]
                if keys[1] in self.names:
                    return ['taken']
                session = json.loads(args[0])
                session.update(startedAt=self.now, endAt=self.now + 900000)
                sid = session['sessionId']
                self.sessions[sid] = session
                self.idempotency[keys[0]] = sid
                self.names[keys[1]] = sid
                return ['created', sid, json.dumps(session)]
            if script == api.MARK_READY:
                sid = keys[0].removeprefix('game:session:')
                session = self.sessions.get(sid)
                if session is None:
                    return None
                session['ready'] = True
                session['messageId'] = args[0]
                return json.dumps(session)
            if script == api.CLAIM_NOTICE:
                sid = keys[0].removeprefix('game:session:')
                session = self.sessions.get(sid)
                if not session or not session['ready'] or (args[0] == 'end' and session['status'] == 'in_progress'):
                    return 0
                notice = args[0] + ':' + args[1]
                if session['notices'].get(notice):
                    return 0
                session['notices'][notice] = True
                return 1
            if script == api.TRANSITION:
                sid = keys[0].removeprefix('game:session:')
                session = self.sessions.get(sid)
                if session is None:
                    return ['missing']
                token_hash, action, version, payload = args
                if token_hash and token_hash != session['tokenHash']:
                    return ['unauthorized']
                if not session['ready']:
                    return ['pending']
                if session['status'] == 'in_progress' and self.now >= session['endAt']:
                    session.update(status='timed_out', submittedAt=session['endAt'], version=session['version'] + 1)
                if action == 'expire':
                    return ['early'] if session['status'] == 'in_progress' else ['ok', json.dumps(session)]
                if action == 'get' or session['status'] != 'in_progress':
                    return ['ok', json.dumps(session)]
                if session['version'] != version:
                    if action == 'progress' and session.get('lastProgress') == payload and session.get('lastProgressVersion') == version:
                        return ['ok', json.dumps(session)]
                    return ['conflict', json.dumps(session)]
                submitted = json.loads(payload)
                session.update(answers=submitted['answersJson'], score=submitted['score'], version=version + 1)
                if action == 'finish':
                    session.update(status='submitted', submittedAt=self.now)
                else:
                    session.update(lastProgress=payload, lastProgressVersion=version)
                return ['ok', json.dumps(session)]
            if script == api.CONFIRM_DELETE:
                sid = keys[1].removeprefix('game:session:')
                session = self.sessions.pop(sid, None)
                if session:
                    self.names.pop(session['nameKey'], None)
                    return json.dumps(session)
                return None
            raise AssertionError('Unexpected script')

    def redis(self, *args):
        if args[0] == 'SISMEMBER':
            return args[2] == '123'
        raise AssertionError('Unexpected Redis command')


class StatefulTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.notices = []
        self.patches = [
            patch.object(api, 'eval_script', side_effect=self.store.eval),
            patch.object(api, 'redis', side_effect=self.store.redis),
            patch.object(api, 'publish', return_value='scheduled-message'),
            patch.object(api, 'send_telegram', side_effect=lambda *args: self.notices.append(args)),
            patch.dict('os.environ', {'TELEGRAM_ADMIN_IDS': '123,456'}),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def create(self, name, key):
        return json.loads(api.register(api.Registration(teamName=name), key).body)

    def test_session_starts_and_expires_without_telegram_admins(self):
        with patch.dict('os.environ', {'TELEGRAM_ADMIN_IDS': ''}):
            session = self.create('Команда без бота', 'no-telegram-idempotency-key')
            self.assertEqual(session['status'], 'in_progress')
            self.assertEqual(session['endAt'] - session['startedAt'], 900000)

            self.store.now = session['endAt']
            result = api.transition(session['sessionId'], '', 'expire')
            self.assertEqual(result['status'], 'timed_out')

        self.assertEqual(self.notices, [])

    def test_independent_sessions_idempotent_save_and_finish(self):
        first = self.create('Первая', 'first-idempotency-key')
        second = self.create('Вторая', 'second-idempotency-key')
        self.assertNotEqual(first['sessionId'], second['sessionId'])
        token = api.digest(first['sessionToken'])
        mutation = api.Mutation(version=0, answers=api.EMPTY, score=3)
        saved = api.transition(first['sessionId'], token, 'progress', mutation)
        retried = api.transition(first['sessionId'], token, 'progress', mutation)
        self.assertEqual(saved['version'], retried['version'])
        with self.assertRaises(HTTPException) as conflict:
            api.transition(first['sessionId'], token, 'progress', api.Mutation(version=0, answers=api.EMPTY, score=4))
        self.assertEqual(conflict.exception.status_code, 409)
        terminal = api.transition(first['sessionId'], token, 'finish', api.Mutation(version=1, answers=api.EMPTY, score=7))
        self.assertEqual(terminal['status'], 'submitted')
        self.assertEqual(api.transition(first['sessionId'], token, 'finish', mutation)['score'], 7)
        self.assertEqual(self.store.sessions[second['sessionId']]['status'], 'in_progress')
        self.assertEqual(len(self.notices), 3)

    def test_timeout_delete_reuse_and_old_expiry(self):
        first = self.create('Команда', 'first-idempotency-key')
        token = api.digest(first['sessionToken'])
        self.store.now = first['endAt']
        terminal = api.transition(first['sessionId'], token, 'progress', api.Mutation(version=0, answers=api.EMPTY, score=20))
        self.assertEqual((terminal['status'], terminal['score']), ('timed_out', 0))
        api.transition(first['sessionId'], '', 'expire')
        self.assertEqual(len(self.notices), 2)
        self.store.eval(api.CONFIRM_DELETE, ['confirm', 'game:session:' + first['sessionId']], ['value'])
        with self.assertRaises(HTTPException):
            api.transition(first['sessionId'], '', 'expire')
        with self.assertRaises(HTTPException):
            self.create('Команда', 'first-idempotency-key')
        second = self.create('команда', 'second-idempotency-key')
        self.assertNotEqual(first['sessionId'], second['sessionId'])
        self.assertEqual(self.store.sessions[second['sessionId']]['status'], 'in_progress')

    def test_finish_competes_with_expiry_and_notifies_once(self):
        first = self.create('Гонка', 'race-idempotency-key')
        self.store.now = first['endAt']
        token = api.digest(first['sessionToken'])
        mutation = api.Mutation(version=0, answers=api.EMPTY, score=10)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(api.transition, first['sessionId'], token, 'finish', mutation),
                       pool.submit(api.transition, first['sessionId'], '', 'expire')]
            outcomes = [future.result() for future in futures]
        self.assertTrue(all(result['status'] == 'timed_out' for result in outcomes))
        self.assertEqual(len(self.notices), 2)
        self.assertEqual(self.notices[0][0], '123')

if __name__ == '__main__':
    unittest.main()

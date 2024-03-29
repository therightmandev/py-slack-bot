import requests
import logging

import tinydb

from static import consts

db = tinydb.TinyDB('database/membersheet.json')

log_level = {'debug': logging.DEBUG,
             'info': logging.INFO,
             'error': logging.ERROR}
logging.basicConfig(filename=consts.LOG_FILE, level=log_level[consts.LOG_LEVEL])

logger = logging.getLogger(__name__)


def sync_new_user(uid, uname, email):
    # {'cheat': 'first_signin'} is a magic value that MUST NOT be used elsewhere
    req = requests.put(consts.DATABASE_URI, timeout=5, cookies={'session': consts.SESSION_ID},
                       params={'email': email, 'username': uname, 'slack_id': uid, 'cheat': 'first_signin'})
    if req.status_code == 200:
        resp = req.json()
        user = resp['response']['value']
        if user is not None:
            for col in ('time', 'github', 'skills'):
                user['!' + col] = user.pop(col)
            db.insert(user)
        else:
            logger.error('DATABASE -- USER NOT FOUND:\n{} ({} - {})'.format(email, uid, uname))
            db.insert(
                {"!skills": '', "!github": '', "!time": '', "email": email, "username": uname,
                 'slack_id': uid, "points": '0'}
            )
    else:
        logger.error('DATABASE -- SOMETHING WENT WRONG: {}\n{} ({} - {})'.format(req.status_code, email, uid, uname))
        db.insert(
            {"!skills": '', "!github": '', "!time": '', "email": email, "username": uname,
             'slack_id': uid, "points": '0'}
        )

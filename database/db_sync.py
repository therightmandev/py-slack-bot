import requests
import logging

import tinydb

from static import consts


class DatabaseWrapper:
    log_level = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'error': logging.ERROR}
    logging.basicConfig(filename=consts.LOG_FILE, level=log_level[consts.LOG_LEVEL])

    logger = logging.getLogger(__name__)
    db = tinydb.TinyDB('database/membersheet.json')

    @classmethod
    def sync_new_user(cls, uid, uname, email):
        req = requests.put(consts.DATABASE_URI, cookies={'session': consts.SESSION_ID},
                           params={'email': email, 'username': uname, 'slack_id': uid})
        if req.status_code == 200:
            resp = req.json()
            user = resp['response']['value']
            if user is not None:
                cls.db.insert(user)
            else:
                cls.logger.error('DATABASE -- USER NOT FOUND:\n{} ({} - {})'.format(email, uid, uname))
                cls.db.insert(
                    {"skills": '', "github": '', "time": '', "email": email, "username": uname,
                     'slack_id': uid, "points": '0'}
                )
        else:
            cls.logger.error('DATABASE -- SOMETHING WENT WRONG: {}\n{} ({} - {})'
                             .format(req.status_code, email, uid, uname))
            cls.db.insert(
                {"skills": '', "github": '', "time": '', "email": email, "username": uname,
                 'slack_id': uid, "points": '0'}
            )

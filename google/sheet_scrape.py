import json
import shutil

import gspread
from oauth2client.client import SignedJwtAssertionCredentials as JwtCred
from tinydb import TinyDB

from static import consts
from database import log


def connect():
    """ Create and authorize a client that has access to the drive API """
    token = json.load(open('static/googleToken.json'))
    scope = ["https://spreadsheets.google.com/feeds/"]

    cred = JwtCred(token['client_email'], token['private_key'].encode(), scope)
    return gspread.authorize(cred)


def update_db():
    """ Scrape sheet and save its content locally """
    db = TinyDB('membersheet.json')

    try:
        client = connect()

        worksheet = client.open_by_key(consts.MEMBERSHEET_ID).sheet1

        vals = worksheet.get_all_values()[1:]
        for row in vals:
            if row[0] != '':
                new_entry = {'name': row[0].lower(),
                             '!time': row[2],
                             '!skills': row[5],
                             '!github': row[7]}
                db.insert(new_entry)
    except Exception as e:
        log.log(str(e), 'sheet_scrape.update_db')
    else:
        shutil.copyfile('membersheet.json', 'database/membersheet.json')
    finally:
        db.purge_tables()

if __name__ == '__main__':
    pass

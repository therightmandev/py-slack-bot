from datetime import datetime, timedelta

from tinydb import TinyDB, Query

from static import consts


def scrape(name, col_name):
    col_name = col_name.lower()

    db = TinyDB('database/membersheet.json')
    found_user = db.search(Query().name == name)

    if len(found_user) != 1:
        return "Couldn't find the user"

    found_user = found_user[0]
    answer = found_user[col_name]

    if answer == '':
        return 'User did not share that information'
    elif col_name == '!time':
        return '{:%H:%M:%S}'.format(datetime.now() + timedelta(hours=int(answer)))
    return answer


# --------- New member -----------
def greet_new_user(userid: str, username: str, slack_client):
    dm_ch = slack_client.api_call('im.open', params={'user': userid})['channel']['id']

    greet_text = "Welcome <@{}>!\n" \
                 "Please take a moment and read this introduction to the system and how it works.\n" \
                 "First of all please type '!membersheet' (w/o quotes) in the chat and access the link I'll give you. "\
                 "You'll find a spreadsheet where you're supposed to enter your information.\n" \
                 "Check out the channels on the left. We have quite a few of them (40+). What you can see right now " \
                 "are all public channels so feel free to join any of them! We have #general and #offtopic to " \
                 "socialize, while other channels serve different purposes. Most CHs are for either language-specific "\
                 "questions, or for projects.\n" \
                 "Enjoy your stay! :simple_smile:" \
        .format(username)
    return {'channel': dm_ch, 'text': greet_text}


def notify_mods(username: str):
    return {'channel': consts.CH_NEW_USER_FEEDBACK, 'text': '{} joined the team'.format(username)}


# -------- Custom functions, append FUNCTION_LIST dict at the bottom --------
def help_(ch: str, **_):
    text = ''.join('{:<40}{}\n'.format(key, val[1]) for key, val in FUNCTION_LIST.items())
    return {'text': 'Currently available commands:\n```{}```'.format(text),
            'channel': ch}


def project_list(ch: str, **_):
    return {'text': 'Currently ongoing projects: {}'.format('http://bit.ly/1PVR3Uy'),
            'channel': ch}


def new_project(ch: str, **_):
    return {'text': 'To start a new project first please fill this form: {}'.format('http://bit.ly/1HQSQYm'),
            'channel': ch}


def membersheet(ch: str, **_):
    return {'text': 'Our member spreadsheet: {}. Please upload your info! Thanks!'.format('http://bit.ly/1R5tvN3'),
            'channel': ch}


def scrape_db(ch: str, msg: str, sender_id: str, slack_client, **_):
    msg = msg.split(' ')
    if len(msg) == 1:
        text = scrape(slack_client.USERS.get(sender_id, ''), msg[0])
    elif len(msg) == 2:
        text = scrape(msg[1], msg[0])
    else:
        text = 'Seems like your message is not formatted correctly. \n' \
               'Correct usage is: "!method" + "username". e.g: "!time daruso"'

    return {'text': text, 'channel': ch}


def admin(ch: str, **_):
    if ch == consts.CH_GENERAL:
        return {'text': '<@joesv> <@micheal> <@daruso> <@therightman>',
                'channel': ch}
    else:
        return {'text': '', 'channel': ch}


def suggest(msg: str, **_):
    return {'text': msg, 'channel': consts.CH_DM_ME}

FUNCTION_LIST = {
    '!help': (help_, ''),
    '!projectlist': (project_list, 'if you want to join an existing project'),
    '!newproject': (new_project, 'if you want to create your own project!'),
    '!membersheet': (membersheet, 'please keep your info up-to-date'),
    '!time': (scrape_db, 'this one has no practical use...    --e.g. !time daruso'),
    '!skills': (scrape_db, 'learn what others are good at    --e.g. !skills daruso'),
    '!github': (scrape_db, "check out other people's work    --e.g. !github daruso"),
    '!admin': (admin, 'will list and tag the admins    --works only in #general, no direct msg'),
    '!suggest': (suggest, 'what you want to see implemented    --e.g. !suggest revive giphy bot')
}

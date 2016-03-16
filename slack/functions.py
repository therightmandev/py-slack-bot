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
def greet_new_user(userid: str, username: str, slack_client) -> dict:
    dm_ch = slack_client.api_call('im.open', params={'user': userid}).get('channel', {}).get('id')

    greet_text = "Welcome <@{}>!\n" \
                 "Please take a moment and read this short introduction\n" \
                 "The channel list is available on the left. Right now you can only see the ones you've joined, " \
                 "but we also have about 60 other. Click on the 'Channels' title (http://i.imgur.com/o3hkfyU.png) to " \
                 "view them all.\n" \
                 "<#{}> is used by the admins to inform you about important stuff. Be sure to check it " \
                 "out if you see a new message there!\n" \
                 "<#{}> is our meta channel. You can suggest or ask about anything that is related to the " \
                 "community.\n" \
                 "<#{}> is used for general programming related discussion. If you have a language-specific " \
                 "question/topic please use the language's channel (if it exists).\n " \
                 "Also I'd like to ask you to type '!membersheet' (without quotes) in the chat, and fill the sheet " \
                 "I'll link you. The '!help' command is also available to find out more about my functions.\n" \
                 "Enjoy your stay! :simple_smile:" \
        .format(username, consts.CH_ANNOUNCEMENTS, consts.CH_ADMIN_HELP, consts.CH_PROGRAMMING)
    return {'channel': dm_ch, 'text': greet_text}


def notify_mods(username: str) -> dict:
    return {'channel': consts.CH_NEW_USER_FEEDBACK, 'text': '{} joined the team'.format(username)}


# -------- Custom functions, append FUNCTION_LIST dict at the bottom --------
def help_(ch: str, **_) -> dict:
    text = ''.join('{:<40}{}\n'.format(key, val[1]) for key, val in FUNCTION_LIST.items())
    return {'text': 'Currently available commands:\n```{}```'.format(text),
            'channel': ch}


def project_list(ch: str, **_) -> dict:
    return {'text': 'Currently ongoing projects: {}'.format('http://bit.ly/1PVR3Uy'),
            'channel': ch}


def new_project(ch: str, **_) -> dict:
    return {'text': 'To start a new project first please fill this form: {}'.format('http://bit.ly/1HQSQYm'),
            'channel': ch}


def membersheet(ch: str, **_) -> dict:
    return {'text': 'Our member spreadsheet: {}. Please upload your info! Thanks!'.format('http://bit.ly/1R5tvN3'),
            'channel': ch}


def scrape_db(ch: str, msg: str, sender_id: str, slack_client, **_) -> dict:
    msg = msg.split(' ')
    if len(msg) == 1:
        text = scrape(slack_client.USERS.get(sender_id, ''), msg[0])
    elif len(msg) == 2:
        text = scrape(msg[1], msg[0])
    else:
        text = 'Seems like your message is not formatted correctly. \n' \
               'Correct usage is: "!method" + "username". e.g: "!time daruso"'

    return {'text': text, 'channel': ch}


def admin(ch: str, **_) -> dict:
    if ch == consts.CH_GENERAL:
        return {'text': '<@joesv> <@micheal> <@daruso> <@therightman>',
                'channel': ch}
    else:
        return {'text': '', 'channel': ch}


def suggest(msg: str, **_) -> dict:
    return {'text': msg, 'channel': consts.CH_DM_ME}


def resources(ch: str, **_):
    if ch == consts.CH_HASKELL:
        return {'text': '<http://learnyouahaskell.com/chapters|Learn You A Haskell>\n\n'
                        '<http://www.seas.upenn.edu/~cis194/lectures.html|CIS194>',
                'channel': ch,
                'as_user': 'true'}
    return ''

FUNCTION_LIST = {
    '!help': (help_, ''),
    '!projectlist': (project_list, 'if you want to join an existing project'),
    '!newproject': (new_project, 'if you want to create your own project!'),
    '!membersheet': (membersheet, 'please keep your info up-to-date'),
    '!time': (scrape_db, 'this one has no practical use...    --e.g. !time daruso'),
    '!skills': (scrape_db, 'learn what others are good at    --e.g. !skills daruso'),
    '!github': (scrape_db, "check out other people's work    --e.g. !github daruso"),
    '!admin': (admin, 'will list and tag the admins    --works only in #general, no direct msg'),
    '!suggest': (suggest, 'what you want to see implemented    --e.g. !suggest revive giphy bot'),
    '!resources': (resources, 'provide some useful links    --works only in #haskell')
}

from telebot.custom_filters import SimpleCustomFilter
from database import connection
c, CONN = connection()

class BotIsAdmin(SimpleCustomFilter):
    key = 'bot_is_admin'
    def __init__(self, bot):
        self.bot = bot
    def check(self, msg):
        try:
            return  self.bot.get_chat_member(msg.chat.id, self.bot.get_me().id).status == "administrator"
        except:
            return self.bot.get_chat_member(msg.message.chat.id, self.bot.get_me().id).status == "administrator"

class CallbackAdmin(SimpleCustomFilter):
    key = 'call_admin'
    def __init__(self, bot):
        self.bot = bot
    def check(self, call):
        return self.bot.get_chat_member(call.message.chat.id,call.message.from_user.id).status in ['administrator','creator']

def is_verified(id):
    CONN.execute("select is_verified from students where user_id = %s", (id, ))

    for verified in CONN.fetchone():

        if verified == "True":
            return True
    return False

def user_lang(user_id: int):
    CONN.execute('SELECT lang FROM students WHERE user_id = %s', (user_id,))
    lang = CONN.fetchone()
    return lang[0]

def creator_id():
    CONN.execute('SELECT user_id, status FROM students')
    for i, s in CONN.fetchall():
        if s == 'creator':
            return i
            
def get_admins():
    import json
    CONN.execute("SELECT admins from bot_setting")
    admins = json.loads(CONN.fetchone()[0])
    return admins

def get_user_p(user_id):
    CONN.execute("SELECT first_name, account_link, gender, status FROM students WHERE user_id = %s", (user_id,))
    name, ac_l, gen, stat = CONN.fetchone()
    if not gen:gen = ""
    return name, ac_l, gen, stat

class IsDeeplinkFilter(SimpleCustomFilter):
    key = 'is_deeplink'
    def check(self, message):
        from telebot.util import is_command
        return len(message.text.split()) > 1 and is_command(message.text.split()[0])

class FromUserFlter(SimpleCustomFilter):
    key = 'from_user'
    def check(self, msg):
        return msg.forward_from is not None

class IsAdminfilter(SimpleCustomFilter):
    key = 'is_admin_or_creator'
    def check(self, message):
        CONN.execute('SELECT status FROM students WHERE user_id = %s', (message.chat.id, ))
        admin = CONN.fetchone()[0]
        if admin == 'admin' or admin == 'creator':
            return True
        else:
            return False

class IsNumberFilter(SimpleCustomFilter):
    key = 'is_number'
    def check(self, message):
        try:
            eval(message.text)
        except:
            return False
        else:
            return True

class NotBannedFilter(SimpleCustomFilter):
    key = 'not_banned'

    def check(self, message):
        CONN.execute("SELECT status FROM students WHERE user_id = %s", (message.from_user.id, ))
        user = CONN.fetchone()
        if user:
            return user[0] != 'banned'
        else:
            return True

class UserJoinedChannelsFilter(SimpleCustomFilter):
    from  telebot import TeleBot
    key = 'joined'
    def __init__(self, bot:TeleBot):
        self.bot = bot

    def check(self, message):
        import json
        joined = True
        CONN.execute("select channels from bot_setting")
        _channels = CONN.fetchone()
        if _channels:
            channels:dict = json.loads(_channels[0])
        else:
            channels = {}
        for channel, val in channels.items():
            if val.get('force_join'):
                try:
                    user = self.bot.get_chat_member(channel, message.from_user.id)
                    if user.status in ['creator', 'administrator', 'member']:
                        joined = True
                    else:
                        joined = False
                except Exception as e:
                    if 'user not found' in e.args[0]:
                        return True

        if joined:
            return True

        else:
            return False
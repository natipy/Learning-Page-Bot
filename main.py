import random
import logging
import re
import generator
import pandas as pd
from text import *
from buttons import *
from database import *
from typing import  Union
import schedule
from time import time
import threading
from system import *
from time_convertor import time_parse as tp
from telebot.custom_filters import *
from telebot.apihelper import ApiTelegramException
from telebot.handler_backends import StatesGroup, State
from telebot import (
    TeleBot,
    types,
    util,
    apihelper
    )
import os
try:
    import de_json as json
except:
    import json
apihelper.ENABLE_MIDDLEWARE = True

db = PrivateDatabase()
conn, cur = connection()
ADMIN_ID = 5213764043
CHANNEL_ID = -1001793167733
TOKEN = os.getenv("bot_token")

bot = TeleBot(TOKEN)

DEEPLINK = 'https://telegram.me/'+bot.get_me().username+'?start='

list_codes = {}
markups = {}

class AskQuestion(StatesGroup):
    question = State()
    subject = State()
    submit = State()
    edit_question = State()

class Answer(StatesGroup):
    answer = State()

class Feedback(StatesGroup):
    Text = State()

class BotSetting(StatesGroup):
    admin = State()
    channel = State()
    balance = State()
class OnMessage(StatesGroup):
    get_msg = State()
    add_btn = State()
    reply = State()
    to_user = State()

    
@bot.message_handler(commands=['start'], chat_types=['private'], is_deeplink=False, joined=True, not_banned=True)
def start_message(msg):
    user_id = msg.chat.id
    date = time()
    inv_link = generator.invite_link(user_id)
    lang = 'empity'
    acc_link = generator.account_link()

    if db.user_is_not_exist(user_id):
        if user_id == ADMIN_ID: status = "creator"
        else: status = "member"
        db.save_data("Student", user_id, date, inv_link, 0, lang, acc_link, "False", status)
    cur.execute('SELECT admins FROM bot_setting')
    ui = cur.fetchone()
    if ui:
        try:
            kwargs = json.loads(ui[0])
        except:
            kwargs = {}
    else:
        kwargs = {}
    lang = user_lang(user_id)
    if lang == 'en':
        bot.send_message(msg.chat.id, "_Select one Option_", reply_markup=main_buttons('en', user_id, **kwargs),
                         parse_mode="Markdown")
    elif lang == 'am':
        bot.send_message(msg.chat.id, "_አንዱን ምርጫ ይምረጡ_", reply_markup=main_buttons('am', user_id, **kwargs),
                         parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "_Select Language / ቋንቋ ይምረጡ_", reply_markup=language_btn(),
                             parse_mode="Markdown")

@bot.message_handler(commands=['start'], is_deeplink=True, chat_types=["private"], not_banned=True)
def start_(msg: types.Message):
    text = msg.text.split()[1]
    cur.execute("SELECT account_link FROM students")
    al = cur.fetchall()
    account_link = [link for links in  al for link in links]
    cur.execute("SELECT browse_link FROM Questions")
    bl = cur.fetchall()
    browse_link = [ui for ux in bl for ui in ux]
    cur.execute("SELECT invitation_link FROM students")
    il = cur.fetchall()
    invitation_link = [link for links in il for link in links]
    cur.execute("SELECT question_link FROM Questions")
    que = cur.fetchall()
    questions = [q for qu in que for q in qu]
    if text == 'start':
        start_message(msg)

    elif text in account_link:
        if db.user_is_not_exist(msg.from_user.id):
            start_message(msg)
            return

        show_account_info(msg, text)

    elif text in browse_link:
        if db.user_is_not_exist(msg.from_user.id):
            start_message(msg)
            return
        cur.execute("SELECT question_id FROM Questions WHERE browse_link = %s", (text,))
        ids = cur.fetchone()[0]
        target = threading.Thread(target=browse, args=(msg, ids))
        target.start()
        target.join()

    elif text in invitation_link:
        cur.execute("SELECT user_id FROM students WHERE invitation_link = %s", (text,))
        user_via_link(msg, cur.fetchone()[0])

    elif text in questions:

        if db.user_is_not_exist(msg.from_user.id):
            start_message(msg)
            return

        cur.execute("SELECT question_id  FROM Questions WHERE question_link = %s", (text,))
        q_id = cur.fetchone()[0]
        lang = user_lang(msg.from_user.id)
        bot.send_message(msg.from_user.id, "<code>Send your answer through Text, Voice or Media(photo, video)</code>",
                         reply_markup=cancel(lang),
                         parse_mode="html")
        bot.set_state(msg.from_user.id, Answer.answer)
        with bot.retrieve_data(msg.from_user.id) as data:
            data['q_id'] = q_id

    else:
        bot.reply_to(msg, "Sorry i don't know your message :(")

@bot.message_handler(commands=['user'], chat_types=['private'], chat_id=[creator_id()])
def free_user(msg: types.Message):
    text = msg.text.split()
    if len(text) == 2:
        try:
            user_id = bot.get_chat(text[1]).id
            cur.execute(
                "SELECT first_name, joined_date, phone_number, gender, username, bio, status FROM students "
                "WHERE user_id  = %s", (user_id,))
            user = cur.fetchone()
            name, jd, phone, gend, us, bio, stat = user
            if stat == 'banned':
                banned = True
            else:
                banned = False
            if not gend: gend = ""
            get = bot.get_chat(user_id)
            bot.send_message(msg.chat.id, f"<b>Name:</b> {name} {gend}\n<b>Phone:</b> <code>{phone}</code>\n" +
                             f"<b>Username:</b> {us}\n<b>Bio:</b> {bio}\n" +
                             f"<b>status:</b> {stat}\n" +
                             f"mention: <a href='tg://user?id={user_id}'>{name}</a>\n" +
                             f"real <a href='tg://user?id={get.id}'>{get.first_name}</a>",
                             parse_mode="HTML", reply_markup=on_user_(user_id, banned, admin_id=creator_id()))

        except Exception:
            bot.send_message(msg.chat.id, "User not found..." )

@bot.callback_query_handler(func=lambda call: call.data in ['am', 'en'], joined=True, not_banned=True)
def update_user_language(call: types.CallbackQuery):
    user_id = call.message.chat.id
    if call.data == 'am':
        db.update_lang(call.data, user_id)
        bot.answer_callback_query(call.id, "ቋንቋዎ ወደ አማርኛ ተቀይሯል ።")
        bot.delete_message(user_id, call.message.id)
        bot.send_message(user_id, "_አንዱን ምርጫ ይምረጡ_", reply_markup=main_buttons('am', user_id), parse_mode="Markdown")
    else:
        db.update_lang(call.data, user_id)
        bot.answer_callback_query(call.id, "Language updated to english.")
        bot.delete_message(user_id, call.message.id)
        bot.send_message(user_id, "_Select one option_", reply_markup=main_buttons('en', user_id),
                         parse_mode="Markdown")


@bot.message_handler(content_types=['contact'], joined=True, not_banned=True)
def register_phone(msg):
    global list_codes
    phone_number = msg.contact.phone_number
    find_phone = re.search(r"^\+?251\d{9}$", phone_number)
    user_id = msg.chat.id
    try:
        if not is_verified(user_id):
            if find_phone:
                try:
                    db.update_phone(user_id, find_phone.group())
                except:
                    raise

                codes = generator.verification_code()
                list_codes[user_id] = codes
                #send_sms(phone_number, "Student", codes)
                lang = user_lang(user_id)
                print(codes)
                if lang == 'am':
                    text = f"የማረጋገጫ ቁጥር ያስገቡ {codes}"

                else:
                    text = f"Enter Your verification code. {codes} "
                ver_code = bot.send_message(msg.chat.id, text, reply_markup=types.ReplyKeyboardRemove())
                bot.register_next_step_handler(ver_code, verifie_am)

            else:
                try:
                    db.ban_user(user_id)
                except:
                    raise
                bot.send_message(user_id, "Banned Number!")

    except ApiTelegramException as e:
        logging.exception(e)

def verifie_am(msg):
    text = msg.text
    user_id = msg.chat.id
    lang = user_lang(user_id)
    if text == list_codes[user_id]:
        if lang == 'am':
            text = "_ምዝገባ በተሳካ ሁነታ ተጠናቋል ።_"
            text_ = "_ከሚከተሉት አንዱን ምርጫ ይምረጡ_"
            btn = main_buttons('am', user_id)

        else:
            text = "_Registration Successfully!_"
            text_ = "_Select one Option_"
            btn = main_buttons('en', user_id)

        bot.send_message(user_id, text, parse_mode='Markdown')
        bot.send_message(msg.chat.id, text_, reply_markup=btn, parse_mode="Markdown")
        try:
            db.set_verifie(user_id)
        except:
            raise
    else:
        ver_code = bot.send_message(user_id, "Invalid Code.Please Try Again.")
        bot.register_next_step_handler(ver_code, verifie_am)

@bot.message_handler(state="*", text=["❌ ሰርዝ", "❌ Cancel"], joined=True, not_banned=True)
def cancel_feedback(msg):
    user_id = msg.chat.id
    start_message(msg)
    bot.delete_state(user_id) 

@bot.message_handler(func=lambda msg: msg.text in en_btns, chat_types=['private'], joined=True, not_banned=True)
def english_button(msg):
    user_id = msg.chat.id
    lang = user_lang(user_id)
    if not lang == 'en':return

    if not is_verified(user_id):
        bot.send_message(user_id, "First send us your phone number through bellow button and register!",
                         reply_markup=en_phone())
        return
    cur.execute(
            "SELECT first_name, joined_date,phone_number,gender,username,bio,lang FROM students WHERE user_id = %s",
        (user_id,))

    first_name, joined_date, phone, gender, username, bio, lang = cur.fetchone()

    if not gender:
        gender = ''

    if msg.text == "📚 Books":
        bot.send_message(user_id, "<i>Select Book Type</i>", parse_mode='HTMl', reply_markup=types_book_am())

    if msg.text == "👨‍👩‍👦‍👦 Invite":
        cur.execute('''
SELECT invitation_link, invites, balance, withdraw, bbalance FROM students join bot_setting WHERE user_id = %s''',
                           (user_id,))
        link, invites, balance, withdr, bbl = cur.fetchone()
        bot.send_message(user_id, BalanceText['en'].format(balance, withdr, invites, bbl, DEEPLINK + link),
                         parse_mode="HTML", reply_markup=withdraw('en', DEEPLINK + link))

    if msg.text == "⚙️ Settings":
        bot.send_message(user_id, SettingText.format(first_name, gender, phone, username, bio, tp(time(), joined_date)),
                         parse_mode="HTML", reply_markup=user_setting(lang))

    if msg.text == "🙋‍♂My Questions":
        target = threading.Thread(target=show_questions, args=(user_id, 'en'))
        target.start()
        target.join()

    if msg.text == "🗣 Ask Question":
        bot.send_message(user_id, "<code>Send your question through Text or media(vedio,voice,photo)</code>",
                         parse_mode="HTML", reply_markup=cancel(lang))
        bot.set_state(user_id, AskQuestion.question)

    if msg.text == "💬 Feedback":
        bot.send_message(user_id, "Send us your feedback", reply_markup=cancel('en'))
        bot.set_state(user_id, Feedback.Text)

@bot.message_handler(func=lambda msg: msg.text in am_btns, chat_types=['private'], joined=True, not_banned=True)
def amharic_button(msg: types.Message):
    user_id = msg.chat.id
    if not is_verified(user_id):
        bot.send_message(user_id, "በቅድሚያ ስልክ ቁጥሮን በመላክ መዝገባ ያከናውኑ!", reply_markup=am_phone())
        return
    lang = user_lang(user_id)
    if not lang == 'am': return
    cur.execute("SELECT first_name,joined_date,phone_number,gender,username,bio FROM students "
                             "WHERE user_id=%s", (user_id,))
    first_name, joined_date, phone, gender, username, bio = cur.fetchone()

    if not gender: gender = ""

    if msg.text == "📚መጽሐፍት":
        bot.send_message(msg.chat.id, "_የመጽሃፍ አይነት ይምረጡ_", parse_mode="Markdown", reply_markup=types_book_am())

    elif msg.text == "👨‍👩‍👦‍👦 ጋብዝ":
        cur.execute('''
SELECT invitation_link, invites, balance, bbalance, withdraw FROM students JOIN bot_setting WHERE user_id = %s''',
                           (user_id,))
        link, invites, balance, withdr, bbl = cur.fetchone()
        bot.send_message(user_id, BalanceText['am'].format(balance, invites, withdr, bbl, DEEPLINK+link),
                         parse_mode="HTML", reply_markup=withdraw('am', DEEPLINK+link))

    elif msg.text == "🙋‍♂ የኔ ጥያቄዎች":
        target = threading.Thread(target=browse, args=(msg, 'am'))
        target.start()
        target.join()

    elif msg.text == "⚙️ ቅንብሮች":
        bot.send_message(user_id, SettingText.format(first_name, gender, phone, username, bio, tp(time(), joined_date)),
                         parse_mode="HTML", reply_markup=user_setting('am'))

    elif msg.text == "🗣 ጥያቄ ጠይቅ":
        bot.send_message(user_id, "<code>ጥያቄዎትን በጽሁፍ ፣ በድምጽ ወይም በምስል (Video,Photo) ይላኩ።</code>",
                         reply_markup=cancel(lang), parse_mode="html")
        bot.set_state(user_id, AskQuestion.question)
    elif msg.text == "💬 አስታየት":
        bot.send_message(user_id, "<code>ያሎትን ሃሳብ ወይም አስታየት ይላኩ።</code>",
                         reply_markup=cancel(lang), parse_mode="html")
        bot.set_state(user_id, AskQuestion.question)


@bot.message_handler(not_banned=False, chat_types=['private'])
def for_banned_user(msg: Union[types.Message, types.CallbackQuery]):
    bot.send_message(msg.chat.id, "💢 You are currently banned from using the bot.")

@bot.message_handler(joined=False, chat_types=['private'])
def join_channel_message(msg: Union[types.Message, types.CallbackQuery]):
    user_id = msg.from_user.id
    cur.execute('select channels from bot_setting')
    channels:dict = json.loads(cur.fetchone()[0])
    username = ''
    for channel, value in channels.items():
        if value['force_join']:
            if not bot.get_chat_member(channel, user_id).is_member:
                username+="@"+bot.get_chat(channel).username+"\n"
    bot.send_message(user_id, f"✳ Dear user first you need to join our channels!\n{username}")

@bot.callback_query_handler(func=lambda call:True, not_banned=False)
def call_banned(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    if call.message.chat.type == 'private':
        for_banned_user(call.message)

@bot.callback_query_handler(func=lambda call:True, joined=False)
def call_banned(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    if call.message.chat.type == 'private':
        join_channel_message(call.message)

@bot.callback_query_handler(func=lambda call: re.match(r"^user", call.data))
def get_user(call: types.CallbackQuery):
    text = call.data.split(":")[1]
    user_id = int(call.data.split(':')[2])
    cur = conn.cursor()
    #
    try:
        cur.execute("SELECT admins FROM bot_setting")
        admins = cur.fetchone()[0]
    except:
        admins = '{}'
    kwargs = json.loads(admins)
    if text == 'ban':
        if int(user_id) == creator_id(): return
        bot.answer_callback_query(call.id, "Banned!")
        db.ban_user(user_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=on_user_(user_id, True, call.message.chat.id, **kwargs))

    elif text == 'show':
        bot.answer_callback_query(call.id)
        cur.execute(
            "SELECT first_name, joined_date, phone_number, gender, username, bio, status FROM students "
            "WHERE user_id  = %s", (user_id,))
        user = cur.fetchone()
        name, jd, phone, gend, us, bio, stat = user

        if not gend: gend = ""
        get = bot.get_chat(user_id)
        bot.send_message(call.message.chat.id, f"<b>Name:</b> {name} {gend}\n<b>Phone:</b> {phone}\n"+
                                            f"<b>Username:</b> {us}\n<b>Bio:</b> {bio}\n"+
                                            f"<b>status:</b> {stat}\n"+
                                            f"mention: <a href='tg://user?id={user_id}'>{name}</a>\n"+
                                            f"real <a href='tg://user?id={get.id}'>{get.first_name}</a>",
                                            parse_mode="HTML")
    elif text == 'unban':
        if int(user_id) == creator_id(): return
        bot.answer_callback_query(call.id, "Unbanned!")
        db.unban_user(user_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=on_user_(user_id, False, call.message.chat.id, **kwargs))
    elif text == "reply":
        admin_id = call.message.chat.id
        bot.send_message(call.message.chat.id, "Hy admin send any message you want to reply", reply_markup=cancel(user_lang(admin_id)))
        bot.set_state(admin_id, OnMessage.reply)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['to'] = user_id

    elif text == 'chat':
        bot.send_message(call.message.chat.id, "Send your message", reply_markup=cancel(user_lang(call.message.chat.id)))
        bot.set_state(call.message.chat.id, OnMessage.to_user)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['to'] = user_id

@bot.callback_query_handler(func=lambda call: re.match(r'^usend', call.data))
def sendmessage(call: types.CallbackQuery):
    user_id = call.data.split(":")[1]
    bot.answer_callback_query(call.id, "Sent")
    name, acc, gen, stat = get_user_p(user_id)
    if stat == 'banned':
        banned = True
    else: banned = False
    user_id = call.data.split(":")[1]
    try:
        kwargs = get_admins()
        bot.copy_message(user_id, call.message.chat.id, call.message.message_id, 
            reply_markup=user_profile_info(call.message.chat.id, banned, user_id, **kwargs))
    except:
        logging.exception("msg cannot be sent")
    finally:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)


def bot_stng_msg(user_id):
    bot.send_message(user_id, f"<b>🤖 Bot Setting</b>\n\nFrom this menu you can manage your bot setting.",
                     reply_markup=bot_setting_btn(), parse_mode='html')



@bot.message_handler(text=["📝 Send Message", "🤖 Bot Setting", "📊 Statics", "🧩 Questions"],
                     is_admin_or_creator=True, chat_types=['private'])
def admins_button(msg: types.Message):
    cur = conn.cursor()
    try:
        cur.execute("SELECT admins FROM bot_setting")
        admin_permision = cur.fetchone()[0]
    except:
        admin_permision = '{}'
    admins: dict = json.loads(admin_permision)
    text = msg.text
    user_id = msg.from_user.id

    if text == "📝 Send Message":
        if user_id == creator_id() or admins[str(user_id)].get('send_message'):
            bot.send_message(user_id, """✳️Enter New Message.\n
You can also «Forward» text from another chat or channel.
            """, reply_markup=cancel('en'))
            bot.set_state(user_id, OnMessage.get_msg)
    elif text == "🤖 Bot Setting":
        if user_id == creator_id() or admins[str(user_id)].get('manage_setting'):
            bot_stng_msg(user_id)

    elif text == "🧩 Questions":
        if user_id == creator_id() or admins[str(user_id)].get('approve_questions'):
            sent = False
            cur.execute("""
                            SELECT students.first_name, students.gender, students.account_link, 
                            Questions.question, Questions.caption,
                            Questions.subject, Questions.type_q, Questions.question_id FROM students 
                            JOIN Questions ON students.user_id = Questions.asker_id
                            WHERE Questions.status = 'pending' ORDER BY time DESC LIMIT 25""")

            for user in cur.fetchall():
                name, gender, acc, q, c, s, tq, q_id = user
                if not gender: gender = ''
                if tq == "Text":
                    bot.send_message(user_id, f"{s}\n\n{q}\n\nBy: <a href='{DEEPLINK+acc}'>{name}</a>{gender}",
                                     reply_markup=question_btn(q_id), parse_mode="html")

                elif tq == "Photo":
                    bot.send_photo(user_id, q, caption=f"{s}\n\n{c}\n\nBy: <a href='{DEEPLINK+acc}'>{name}</a>{gender}",
                                   reply_markup=question_btn(q_id), parse_mode="html")

                elif tq == "Voice":
                    bot.send_voice(user_id, q, caption=f"{s}\n{c}\nBy: <a href='{DEEPLINK+acc}'>{name}</a>{gender}",
                                   reply_markup=question_btn(q_id), parse_mode="html")

                else:
                    bot.send_video(user_id, q, caption=f"{s}\n\n{c}\n\nBy: <a href='{DEEPLINK+acc}'>{name}</a>{gender}",
                                   reply_markup=question_btn(q_id), parse_mode="html")
                sent = True

            if not sent:
                bot.send_message(user_id, "There is no question yet.")

    else:
        if user_id == creator_id() or admins[str(user_id)].get('can_see'):
            cur.execute("SELECT count(user_id) FROM students")
            count = cur.fetchone()[0]
            cur.execute("SELECT first_name, account_link, gender FROM students ORDER BY joined_date LIMIT 10")
            users = cur.fetchall()
            ls = []
            for n, a, g in users:
                if not g:
                    g = ''
                ls.append(f'[{n}]({DEEPLINK+a}) {g}')
            coll = [str(j+1) + " "+i+'\n' for j, i in enumerate(pd.Series(ls))]
            bot.send_message(user_id, '\n'.join(coll)+f'\n\nShowed {len(ls)}: Total {count}', parse_mode='markdown')


@bot.message_handler(state=OnMessage.get_msg, content_types=util.content_type_media)
def on_get_message(msg: types.Message):
    btn = types.InlineKeyboardMarkup()
    
    btn.add(
        types.InlineKeyboardButton("➕ Add", callback_data=f'sm:add'),
        types.InlineKeyboardButton("☑ Done", callback_data=f'sm:done')
    )
    bot.copy_message(msg.chat.id, msg.chat.id, msg.message_id, parse_mode='html', reply_markup=btn)
    start_message(msg)

@bot.callback_query_handler(func=lambda call: re.match('^sm', call.data))
def on_got_message(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    c = call.data.split(':')[1]
    if c == 'add':
        bot.send_message(call.message.chat.id, "Send your button link this:\n"
                                                "text -> www.text.com")
        bot.set_state(call.message.chat.id, OnMessage.add_btn)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['msg_id'] = call.message.message_id
    
    elif c == 'done':
        send_to_users(call)
        
@bot.message_handler(state=OnMessage.add_btn)
def on_send_btn(msg: types.Message):
    text = msg.text
    match = re.findall(r"\w+\s*->\s*[a-zA-Z@0-9.]+", text)
    if match:
        btns = {k.split('->')[0]:k.split('->')[1] for k in match}
        for k, v in btns.items():
            markups[k]={'url':v.lstrip()}
        markups["➕ Add"] = {'callback_data':f'sm:add'}
        markups["☑ Done"] = {'callback_data':f'sm:done'}
        try:
            with bot.retrieve_data(msg.chat.id) as data:
                msg_id = data['msg_id']
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, parse_mode='html', 
            reply_markup=util.quick_markup(markups))
        except Exception as e:
            bot.reply_to(msg, e.args[0])
            bot.reply_to(msg, "Invalid Url link ...")
    else:
        bot.reply_to(msg, "error")

def channel_text():
    try:
        cur.execute("SELECT channels FROM bot_setting")
        channels = cur.fetchone()[0]
    except:
        channels = '{}'
   
    channels = json.loads(channels)
    chan = [bot.get_chat(c) for c in channels if c]
    ch = [c.username for c in chan]
    chan = '\n'.join(ch)
    key = [key for key, val in channels.items()]
    key = [bot.get_chat(k) for k in key]
    ukey = {k.username: {'callback_data': "channel:" + str(k.id)} for k in key}
    ukey.update({"➕ Add": {'callback_data': "bot:add_channel"}, "🔙 Back": {"callback_data": 'bot:back'}})
    return CHANNEL.format(chan), util.quick_markup(ukey)


def admin_text():
    try:
        cur.execute("SELECT admins FROM bot_setting")
        admins = cur.fetchone()[0]
    except:
        admins = '{}'
    admins = json.loads(admins)
    ad = [bot.get_chat(c) for c in admins]
    ad = [chaneel.first_name for channel in ad]
    ad = '\n'.join(ad)
    key = [bot.get_chat(key) for key in admins]

    ukey = {k.first_name: {'callback_data': "badm:" + str(k.id)} for k in key}
    ukey.update({"➕ Add": {'callback_data': "bot:add_admin"}, "🔙 Back": {"callback_data": 'bot:back'}})
    return ADMIN.format(ad), util.quick_markup(ukey)

@bot.callback_query_handler(func=lambda call: re.match(r"^bot:", call.data))
def on_bot_setting(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    text = call.data.split(':')[1]
    user_id = call.message.chat.id
    msg_id = call.message.message_id
    if text == 'balance':
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("🆙 Update", callback_data='bot:ubalance'),
                types.InlineKeyboardButton("🔙 Back", callback_data='bot:back'))
        cur.execute("SELECT bbalance FROM bot_setting")
        b = cur.fetchone()[0]
        bot.edit_message_text(f"Current balance: {b} Birr", user_id, call.message.message_id, reply_markup=btn)

    elif text == 'ubalance':
        bot.edit_message_reply_markup(user_id, msg_id, reply_markup=None)
        bot.send_message(user_id, "Send new balance what a user get when he invite person",
                         reply_markup=types.ForceReply())
        bot.set_state(user_id, BotSetting.balance)

    elif text == 'channels':
        t, k = channel_text()
        bot.edit_message_text(t, call.message.chat.id, call.message.message_id,
                              reply_markup=k, parse_mode='html')

    elif text == 'admins':
        a, k = admin_text()
        bot.edit_message_text(a, call.message.chat.id, call.message.message_id,
                              reply_markup=k, parse_mode='html')

    elif text == 'add_channel':
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, ADD_CHANNEL, reply_markup=bscancel(), parse_mode='html')
        bot.set_state(user_id, BotSetting.channel)

    elif text == 'add_admin':
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, ADD_ADMIN, reply_markup=bscancel(), parse_mode='html')
        bot.set_state(user_id, BotSetting.admin)

    elif text == 'back':
        bot.edit_message_text(f"<b> 🤖 Bot Setting</b>\n\nFrom this menu you can manage your bot setting.", user_id,
        msg_id, reply_markup=bot_setting_btn(), parse_mode='html')

@bot.message_handler(state=BotSetting.balance, is_number=True, chat_types=['private'])
def set_balance(msg: types.Message):
    bot.delete_message(msg.chat.id, msg.message_id-2)
    bot.send_message(msg.chat.id, "Balance updated ✅")
    db.update_bot_balance(msg.text)
    cur = conn.cursor()
    btn = types.InlineKeyboardMarkup()
    btn.add(types.InlineKeyboardButton("🆙 Update", callback_data='bot:ubalance'),
            types.InlineKeyboardButton("🔙 Back", callback_data='bot:back'))
    cur.execute("SELECT bbalance FROM bot_setting")
    b = cur.fetchone()[0]
    bot.send_message(msg.from_user.id, f"Current balance: {b} Birr", reply_markup=btn)
    start_message(msg)

@bot.callback_query_handler(func=lambda call: call.data == 'bscancel', state='*')
def cancel_on_add_admin(call: types.CallbackQuery):
    state = bot.get_state(call.message.chat.id)
    bot.answer_callback_query(call.id)
    bot.delete_state(call.message.chat.id)
    t, k = channel_text()
    if state == BotSetting.channel:
        bot.edit_message_text(CHANNEL.format(t), call.message.chat.id, call.message.message_id,
                          reply_markup=k, parse_mode='html')
    else:
        a, k = admin_text()
        bot.edit_message_text(ADMIN.format(a), call.message.chat.id, call.message.message_id,
                              reply_markup=k, parse_mode='html')


@bot.message_handler(state=BotSetting.channel, is_forwarded=True)
def add_channel(msg: types.Message):
    channel = msg.forward_from_chat
    user_id = msg.from_user.id
    try:
        assert channel.type == 'channel', "Must be channel not "+channel.type
        assert channel.username, "the channel must have a username!"
        cur.execute("select channels from bot_setting")
        ujson: dict = json.loads(cur.fetchone()[0])
        ujson.update({str(channel.id):
                              {'send_message':False, 'approve':False, 'force_join':False}})
        cur.execute("update bot_setting set channels = %s", (json.dumps(ujson),))
        conn.commit()
        bot.send_message(user_id, "Channel added successfully ✅")
        t, k = channel_text()
        bot.send_message(user_id, CHANNEL.format(t), reply_markup=k, parse_mode='html')
    except AssertionError as e:
        bot.send_message(user_id, e.args[0])
        bot.set_state(user_id, BotSetting.channel)
    except Exception as e:
        print(e)
    else:
        bot.delete_state(user_id)
    finally:
        return True

def admin_permision(admin_id, o_ad=False):
    cur.execute("select admins from bot_setting")
    ujson:dict = json.loads(cur.fetchone()[0])
    cur.execute("select status from students where user_id = %s", (admin_id,))
    stat = cur.fetchone()[0]
    per = ['✅' if ujson[str(admin_id)][key] else "❌" for key in ujson.get(str(admin_id))]
    admin = bot.get_chat(admin_id)
    text = ADMINP.format(admin.first_name, *per)
    btn = admin_permision_btn(admin_id, stat, **ujson)
    return text, btn

def channel_permision(channel_id):
    cur.execute("select channels from bot_setting")
    ujson:dict = json.loads(cur.fetchone()[0])
    per = ['✅' if ujson[channel_id][key] else "❌" for key in ujson.get(channel_id)]
    channel = bot.get_chat(channel_id)
    text = CHANNELP.format(channel.username, *per)
    btn = channel_btn(channel_id, **ujson)
    return text, btn

@bot.message_handler(state=BotSetting.admin, content_types=util.content_type_media, is_digit=True)
def add_admin(msg: types.Message):
    user_id = msg.from_user.id
    user = int(msg.text)
    try:
        assert not db.user_is_not_exist(user), "User not found"
        cur.execute("select status from students where user_id = %s", (user,))
        assert cur.fetchone()[0] not in ['creator', 'admin'], "User is already admin!"
        cur.execute("select admins from bot_setting")
        ujson: dict = json.loads(cur.fetchone()[0])
        ujson.update({
            str(user):{"send_message":False, 'approve_questions': False, 'manage_setting':False, 'ban_user':False,
                          'feedback':False, 'can_see':False}
        })
        cur.execute("update bot_setting set admins = %s", (json.dumps(ujson),))
        conn.commit()
        bot.send_message(user_id, "Admin added successfully ✅")
        text, btn = admin_permision(user, 'member')
        bot.send_message(user_id, text, reply_markup=btn, parse_mode='html')

    except AssertionError as e:
        bot.send_message(user_id, e.args[0])
    finally:
        bot.delete_state(user_id)

@bot.callback_query_handler(func=lambda call: re.search(r'channel:', call.data))
def click_channel(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id, msg_id = call.from_user.id, call.message.message_id
    channel_id = call.data.split(':')[1]
    t, b = channel_permision(channel_id)
    bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')

@bot.callback_query_handler(func=lambda call:re.search(r'myc', call.data))
def on_channel_permision(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    channel_id = call.data.split(":")[1]
    text = call.data.split(":")[2]
    user_id = call.from_user.id
    msg_id = call.message.message_id
    if text == 'back':
        t, b = channel_text()
        bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')
    elif text == 'remove':
        try:
            cur.execute('select channels from bot_setting')
            ujson:dict = json.loads(cur.fetchone()[0])
            del ujson[channel_id]
            cur.execute('update bot_setting set channels = %s', (json.dumps(ujson),))
            conn.commit()
            t, b = channel_text()
            bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')
        except:
            bot.send_message(user_id, "channel not found..")
            bot.delete_message(user_id, msg_id)
    else:
        try:
            cur.execute('select channels from bot_setting')
            ujson: dict = json.loads(cur.fetchone()[0])
            if ujson[channel_id][text]:
                ujson[channel_id][text] = False
            else:
                ujson[channel_id][text] = True
            cur.execute("update bot_setting set channels = %s", (json.dumps(ujson),))
            conn.commit()
            t, b = channel_permision(channel_id)
            bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')

        except:
            bot.send_message(user_id, "channel not found...")
            bot.delete_message(user_id, msg_id)

@bot.callback_query_handler(lambda call: re.search(r"badm", call.data))
def click_admin(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    admin_id = call.data.split(':')[1]
    text, btn = admin_permision(admin_id)
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=btn, parse_mode='html')

@bot.callback_query_handler(lambda call: re.search(r'admin:', call.data))
def on_admin_permision(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    admin_id = call.data.split(":")[2]
    user_id = call.from_user.id
    msg_id = call.message.message_id
    text = call.data.split(":")[1]
    kwargs = {'send_message': "Send message to users and channels", 'manage_setting': "Manage bot setting",
              'approve_questions': "Approve questions", 'ban_user': "Ban user", 'feedback': "Recieve feedback",
              'can_see': "See users' profile and Bot Stastics"}

    if text == 'done':
        try:
            cur.execute("update students set status = 'admin' where user_id = %s", (admin_id,))
            conn.commit()
            cur.execute('select admins from bot_setting')
            ujson: dict = json.loads(cur.fetchone()[0])
            per = ["◽ "+kwargs[key] for key, val in ujson.get(admin_id, {}).items() if val]
            per = '\n'.join(per)
            bot.send_message(int(admin_id), "🎉 Dear user you have been made as an admin on this bot and you have these "
                                            f"permision(s) 👇\n{per}\n\n"
                                            f"💠 [Click here to activate your permision]({DEEPLINK+'start'}",
                                            parse_mode='markdown')
            t, k = admin_text()
            bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')

        except Exception as e:
            bot.send_message(user_id, e.args[0])
            bot.delete_message(user_id, msg_id)

    elif text == 'back':
        t, k = admin_text()
        bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')
    elif text == 'remove':
        try:
            cur.execute("update students set status = 'member' where user_id = %s", (admin_id,))
            conn.commit()
            cur.execute('select admins from bot_setting')
            ujson: dict = json.loads(cur.fetchone()[0])
            del ujson[admin_id]
            cur.execute('update bot_setting set admins = %s', (json.dumps(ujson),))
            conn.commit()
        except:
            bot.send_message(user_id, "user not found....")
            bot.delete_message(user_id, msg_id)
        else:
            t, k = admin_text()
            bot.edit_message_text(ADMIN.format(t), user_id, msg_id, reply_markup=k, parse_mode='html')

    else:
        try:
            cur.execute('select admins from bot_setting')
            ujson: dict = json.loads(cur.fetchone()[0])
            if ujson[admin_id][text]:
                ujson[admin_id][text] = False
            else:
                ujson[admin_id][text] = True
            cur.execute('update bot_setting set admins = %s', (json.dumps(ujson),))
            conn.commit()
        except:
            bot.send_message(user_id, "user not found...")
            bot.delete_message(user_id, msg_id)
        else:
            t, k = admin_permision(admin_id, False)
            bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')

@bot.message_handler(state=OnMessage.reply, content_types=util.content_type_media)
def replytouser(msg: types.Message):
    with bot.retrieve_data(msg.chat.id) as data:
        user_id = data['to']
    bot.send_message(msg.chat.id, "sent!")
    bot.copy_message(user_id, msg.chat.id, msg.message_id, parse_mode = 'html')    
    start_message(msg)

@bot.message_handler(state=OnMessage.to_user, content_types = util.content_type_media)
def sendtouser(msg: types.Message):
    with bot.retrieve_data(msg.chat.id) as data:
        user_id = data['to']
    name, acc, gen, stat = get_user_p(user_id)
    btn = types.InlineKeyboardMarkup()
    btn.add(types.InlineKeyboardButton("✅ Send", callback_data=f'usend:{user_id}'))
    bot.copy_message(msg.chat.id, msg.chat.id, msg.message_id, caption=f"[{name}]({DEEPLINK+acc}) {gen}",
        parse_mode='markdown', reply_markup=btn)
    start_message(msg)
    bot.delete_state(msg.chat.id)

@bot.callback_query_handler(func=lambda call: re.match(r"^uq", call.data))
def approve_or_decline(call: types.CallbackQuery):
    text = call.data.split("_")[1]
    q_id = call.data.split("_")[2]
    cur = conn.cursor()
    try:
        cur.execute("SELECT channels FROM bot_setting")
        channel = cur.fetchone()[0]
    except:
        channel = "{}"
    ch: dict = json.loads(channel)
    ch_u, ch_i = None, None
    cur.execute("SELECT asker_id FROM Questions  WHERE question_id = %s", (q_id,))
    user_id = cur.fetchone()[0]
    for key, val in ch.items():
        if val.get('approve'):
            ch_u = bot.get_chat(key).username
            ch_i = key
            break
    if not ch_u:
        bot.answer_callback_query(call.id, "No channel is satted for approve question!", show_alert=True)
        bot.delete_message(call.from_user.id, call.message.message_id)
        return
    cur.execute('SELECT status FROM Questions WHERE question_id = %s', (q_id,))
    status = cur.fetchone()[0]
    if text == "approve":
        if (status == 'approved') or (status == "declined"):
            if status == 'approved':
                cur.execute('SELECT message_id FROM Questions WHERE question_id = %s', (q_id,))
                msg_id = cur.fetchone()[0]
                show = types.InlineKeyboardMarkup()
                show.add(types.InlineKeyboardButton("👀 Show me", url=ch_u + '/' + str(msg_id)))
                bot.answer_callback_query(call.id, "This question is already approved!")
                bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=show)
            else:
                bot.answer_callback_query(call.id, "This question is already declined!")
                bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=None)
            return

        cur.execute("SELECT question_link, browse_link, browse FROM Questions "
                     "WHERE question_id = %s", (q_id,))
        ql, bl, b = cur.fetchone()
        btn = types.InlineKeyboardMarkup()
        btn.add(
            types.InlineKeyboardButton("Answer", url=DEEPLINK+ql),
            types.InlineKeyboardButton(f"Browse ({b})", url=DEEPLINK+bl)
        )
        msg=bot.copy_message(ch_i, call.message.chat.id, call.message.message_id, 
                parse_mode='markdown', reply_markup=btn)
        
        cur.execute("UPDATE Questions SET status = 'approved', message_id = %s"
                     " WHERE question_id = %s", (msg.message_id, q_id))
        conn.commit()
        ch_u = 'https://t.me/'+ch_u
        show = types.InlineKeyboardMarkup()
        show.add(types.InlineKeyboardButton("👀 Show me", url=ch_u+'/'+str(msg.message_id)))
        d = types.InlineKeyboardMarkup()
        d.add(types.InlineKeyboardButton('🗑 Delete', callback_data=f'uq_delete_{msg.message_id}'))
        bot.answer_callback_query(call.id, "Approved!")
        bot.send_message(user_id, "Your question is approved!", reply_markup=show)
        bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=d)
        bot.answer_callback_query(call.id, "Question is approved")

    elif text == 'decline':
        cur.execute("UPDATE Questions SET status = 'declined' WHERE question_id = %s",
                     (q_id,))
        conn.commit()
        btn = types.InlineKeyboardMarkup()
        approve = types.InlineKeyboardButton(text="⏫ Re approve", callback_data=f'uq_approve_{q_id}')
        btn.add(approve)
        bot.send_message(user_id, "sorry your question is not related to education and was declined!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=btn)

    elif text == 'delete':
        cur.execute("SELECT message_id FROM Questions WHERE question_id = %s", (q_id,))
        msg_id = cur.fetchone()[0]
        try:
            bot.answer_callback_query(call.id, "Deleted")
            bot.delete_message(ch_i, msg_id)

        except Exception as e:
            bot.send_message(user_id, e.args[0])
        finally:
            bot.delete_message(user_id, call.message.message_id)

@bot.message_handler(commands=['lang'], chat_types=['private'], joined=True, not_banned=True)
def lang_command(msg):
    bot.send_message(msg.chat.id, "_Select Language / ቋንቋ ይምረጡ_",
                     reply_markup=language_btn(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == 'ask_question', joined=True, not_banned=True)
def askquestion(call):
    user_id = call.from_user.id
    bot.delete_message(user_id, call.message.id)
    lang = user_lang(user_id)
    if lang == 'am':
        bot.send_message(user_id, "<code>ጥያቄዎትን በጽሁፍ ፣ በድምጽ ወይም በምስል (Video,Photo) ይላኩ።</code>",
                         reply_markup=cancel(lang), parse_mode="html")
        bot.set_state(user_id, AskQuestion.question)
    elif lang == 'en':
        bot.send_message(user_id, "<code>Send your question through Text or media(vedio,voice,photo)</code>",
                         parse_mode="HTML", reply_markup=cancel(lang))
        bot.set_state(user_id, AskQuestion.question)

@bot.callback_query_handler(func=lambda call:call.data == 'report')
def report_answer(call: types.CallbackQuery):
    user_id = call.data.split(":")[1]
    name, acc, gen, stat = get_user_p(user_id)
    if stat == 'banned':
        banned = True
    else:
        banned = False
    bot.answer_callback_query(call.id, "Reported!")
    bot.send_message(creator_id(), "One message were reported")
    bot.copy_message(creator_id(), call.message.chat.id, call.message.message_id, reply_markup=on_user_(user_id, banned, creator_id()))

@bot.message_handler(state=Feedback.Text, content_types=util.content_type_media, joined=True, not_banned=True)
def user_feedback(msg):
    user_id = msg.chat.id
    cur = conn.cursor()
    lang = user_lang(user_id)
    if msg.text:
        cur.execute("select first_name, account_link, gender from students where user_id = %s", (user_id,))
        name, link, gend = cur.fetchone()
        if not gend:
            gend = ''
        bot.send_message(user_id, "Thank you for your comment!" if lang == 'en' else "ስለ አስታየቶ ከልብ እናመሰግናለን ።")
        start_message(msg)
        bot.send_message(creator_id(), f"""#Feedback !\n\n*{msg.text}*\n
From: [{name}]({DEEPLINK+link}) {gend}
""", reply_markup=on_user_(user_id, banned=False, admin_id=creator_id()),
parse_mode="Markdown", disable_notification=False)
        cur.execute("SELECT admins FROM bot_setting")
        admin: dict = json.loads(cur.fetchone()[0])
        for key, val in admin.items():
            if val.get('feedback'):
                try:
                    bot.send_message(int(key), f"""#Feedback !\n\n*{msg.text}*\n
                    From: [{name}]({DEEPLINK + link}) {gend}
                    """, reply_markup=on_user_(user_id, banned=False, admin_id=int(key),
                    msg_id=msg.message_id,  **admin), parse_mode="Markdown", disable_notification=False)
                except: continue
    else:
        bot.send_message(user_id, "Text is required!")
        bot.set_state(user_id, Feedback.Text)

@bot.message_handler(state=AskQuestion.question, content_types=['text', 'photo', 'voice', 'video'],
                     joined=True, not_banned=True)
def ask_question(msg):
    user_id = msg.chat.id
    lang = user_lang(user_id)
    with bot.retrieve_data(user_id) as Question:
        if msg.content_type == "text":
            Question['text'] = msg.text
        
        elif msg.content_type == "photo":
            if msg.caption is not None:
                Question['text'] = ["Photo", msg.caption, msg.photo[-1].file_id]
            else:
                bot.send_message(user_id, "Sorry the photo has not a caption. please send with a caption ")
                bot.set_state(user_id, AskQuestion.question)
                return

        elif msg.content_type == "voice":
            Question['text'] = ['Voice', msg.caption, msg.voice.file_id]
            
        else:
            if msg.caption is not None:
                Question['text'] = ['Video', msg.caption, msg.video.file_id]
            else:
                bot.send_message(user_id, "Sorry the video has not a caption. please send with a caption ")
                bot.set_state(user_id, AskQuestion.question)
                return

    if lang == 'en':
        text = "select subject of your question"
    else:
        text = "የጥያቄዎን የትምህርት አይነት ይምርጡ"
    bot.send_message(user_id, text, reply_markup=subject_btn(lang))
    bot.set_state(user_id, AskQuestion.subject)

@bot.message_handler(state=AskQuestion.subject, joined=True, not_banned=True)
def response_question(msg):
    user_id = msg.from_user.id
    subject = msg.text
    lang = user_lang(user_id)
    cur = conn.cursor()
    if subject == "🇬🇧 English":
        subje = '#English'

    elif subject == "🇪🇹 አማርኛ":
        subje = "#Amharic"

    elif subject == "⚽️ HPE":
        subje = "#HPE"
    else:
        subject = msg.text[1:].strip()
        subje = "#"+subject
    with bot.retrieve_data(user_id) as Question:
        Question['subject'] = subje
    cur.execute('select first_name,account_link,gender from students where user_id = %s', (user_id,))
    name, acc, gend = cur.fetchone()

    if not gend:
        gend = ''

    if msg.text in subj:
        with bot.retrieve_data(user_id) as Data:
            data = Data['text']
            if isinstance(data, str):
                text = f"{data}"
                db.save_question(user_id, text, "Text", subje, generator.question_link(), generator.browse_link())
                cur.execute("SELECT MAX(question_id) FROM Questions")
                q_id = cur.fetchone()[0]
                bot.send_message(user_id, f"{subje}\n\n*{data}*\nBy: [{name}]({DEEPLINK+acc}) {gend}",
                                 reply_markup=Panel(q_id), parse_mode="Markdown")
                
            else:
                caption = data[1]
                file = data[2]

                if caption is None:
                    caption = ""

                if data[0] == "Photo":
                    db.save_question(user_id, file, "Photo", subje, generator.question_link(),
                                     generator.browse_link(), caption)
                    system = bot.send_photo

                elif data[0] == "Video":
                    db.save_question(user_id, file, "Video", subje, generator.question_link(),
                                     generator.browse_link(), caption)
                    system = bot.send_video

                else:
                    db.save_question(user_id, file, "Voice", subje, generator.question_link(),
                                     generator.browse_link(), caption)
                    system = bot.send_voice

                cur.execute('SELECT MAX(question_id) FROM Questions')
                q_id = cur.fetchone()[0]

                system(user_id, file, caption=f"{subje}\n\n*{caption}*\n\nBy: [{name} ]({DEEPLINK+acc}) {gend}",
                       parse_mode="Markdown", reply_markup=Panel(q_id))
            bot.send_message(user_id, "When you finish preveiwing your question press submit button!")
        start_message(msg)

    else:
        bot.send_message(msg.chat.id, "Please use only bellow button!", reply_markup=subject_btn(lang))
        bot.set_state(msg.chat.id, AskQuestion.subject)
        
@bot.callback_query_handler(func=lambda call: re.search('^(send_|edit_|del_)', call.data), joined=True, not_banned=True)
def submit_question(call: types.CallbackQuery):
    user_id = call.from_user.id
    cur = conn.cursor()
    lang = user_lang(user_id)
    text = call.data.split("_")[0]
    q_id = call.data.split("_")[1]
    if text == 'send':
        bot.answer_callback_query(call.id, "Your question will be approved by admin!", show_alert=True)
        cur.execute("UPDATE Questions SET status = 'pending' WHERE question_id = %s", (q_id,))
        conn.commit()
        msg = call.message
        bot.edit_message_reply_markup(call.from_user.id, msg.message_id, reply_markup=on_user_question('pending', q_id))
        bot.delete_state(call.from_user.id)

    elif text == 'edit':
        cur.execute("DELETE FROM Questions WHERE question_id = %s", (q_id,))
        conn.commit()
        bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=None)
        bot.send_message(user_id, "Send new your question.", reply_markup=cancel(lang))
        bot.set_state(user_id, AskQuestion.question)

    else:
        bot.answer_callback_query(call.id, "Question has been deleted!")
        cur.execute("DELETE FROM Questions WHERE question_id = %s", (q_id,))
        conn.commit()
        bot.delete_message(user_id, call.message.id)
        bot.delete_state(user_id)
        start_message(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q:"))
def on_questions_status(call: types.CallbackQuery):
    q_id = call.data.split(":")[2]
    text = call.data.split(":")[1]
    user_id = call.from_user.id
    cur = conn.cursor()
    cur.execute("SELECT status, asker_id FROM Questions WHERE question_id = %s", (q_id,))
    status, q_u_id = cur.fetchone()

    if not user_id != q_u_id:
        bot.answer_callback_query(call.id, "Something went wrong....")
        bot.delete_message(user_id, call.message.message_id)
        return

    if text == 'cancel':

        if status == 'pending':
            bot.answer_callback_query(call.id, "question was canceld!")
            cur.execute("UPDATE Questions SET status = 'canceld' WHERE question_id = %s", (q_id,))
            conn.commit()
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id,
                                          reply_markup=on_user_question('canceld', q_id))

        elif status == 'canceld':

            bot.answer_callback_query(call.id, "This questions already canceld!", show_alert=True)
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id,
                                          reply_markup=on_user_question('canceld', q_id))

        elif status == 'approved':
            bot.answer_callback_query(call.id, "This question already approved!", show_alert=True)
            bot.delete_message(call.from_user.id, call.message.message_id)

        else:
            bot.answer_callback_query(call.id, "something went wrong :(")

    else:

        if status == 'canceld':
            bot.answer_callback_query(call.id, "question submited!")
            cur.execute("UPDATE Questions SET status = 'pending' WHERE question_id = %s", (q_id,))
            conn.commit()
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id,
                                          reply_markup=on_user_question('pending', q_id))

        elif status == 'resubmit':
            bot.answer_callback_query(call.id, "This questions is already submited!", show_alert=True)
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id,
                                          reply_markup=on_user_question('pending', q_id))

        elif status == 'approved':
            bot.answer_callback_query(call.id, "This question is already approved!", show_alert=True)
            bot.delete_message(call.from_user.id, call.message.message_id)

        else:
            bot.answer_callback_query(call.id, "something went wrong :(")

@bot.callback_query_handler(func=lambda c: re.search('^answer', c.data), joined=True, not_banned=True)
def answer_questions(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    msg = call.message
    q_id = int(call.data.split('_')[1])
    lang = user_lang(msg.chat.id)
    bot.send_message(msg.chat.id, "<code>Send your answer through Text, Voice or Media(photo, video)</code>",
                     reply_markup=cancel(lang), parse_mode="html")
    bot.set_state(msg.chat.id, Answer.answer)
    with bot.retrieve_data(msg.chat.id) as data:
        data['q_id'] = q_id

@bot.message_handler(state=Answer.answer, content_types=['text', 'photo', 'voice', 'video'],
                     joined=True, not_banned=True, chat_types=['private'])
def on_preview_answer(msg: types.Message):
    user_id = msg.from_user.id
    with bot.retrieve_data(user_id) as data:
        q_id = data.get('q_id')
        is_reply = data.get('on_reply')

    text = msg.text
    photo = msg.photo
    video = msg.video
    voice = msg.voice
    if  q_id is None:
        q_id = is_reply['question_id']
    if text:
        caption = ""
        typ = "Text"
        ans = text

    elif photo:
        typ = "Photo"
        caption = msg.caption
        if not caption:
            bot.send_message(user_id, "The photo has not caption. please send with caption!")
            bot.set_state(user_id, Answer.answer)
            return
        ans = photo[-1].file_id

    elif video:
        typ = "Video"
        caption = msg.caption
        if not caption:
            bot.send_message(user_id, "The video has not caption. please send with caption!")
            bot.set_state(user_id, Answer.answer)
            return

        ans = video.file_id
    else:
        typ = "Voice"
        caption = msg.caption
        ans = voice.file_id
        if not caption: caption = ''
    if is_reply:
        reply_to = is_reply['to_id']
    else:
        reply_to = 0
    db.insert_answer(user_id, q_id, ans, typ, generator.question_link(), caption, reply_to)
    cur.execute("SELECT MAX(answer_id) FROM Answers")
    a_ = cur.fetchone()[0]
    cur.execute("SELECT first_name, gender, account_link FROM students "
                                      "WHERE user_id = %s", (user_id,))
    name, gender, link = cur.fetchone()
    if not gender: gender = ""
    if text:
        bot.send_message(user_id, f"{text}\n\nBy: [{name}]({DEEPLINK+link}) {gender}",
                             parse_mode="markdown", reply_markup=answer_btn(q_id, a_))

    elif photo:
        bot.send_photo(user_id, ans, caption=f"{caption}\n\nBy: [{name}]({DEEPLINK+link}) {gender}",
                              parse_mode="markdown", reply_markup=answer_btn(q_id, a_))
    elif video:
        bot.send_video(user_id, ans, caption=f"{caption}\n\nBy: [{name}]({DEEPLINK + link}) {gender}",
                       parse_mode="markdown", reply_markup=answer_btn(q_id, a_))
    else:
        bot.send_voice(user_id, ans, caption=f"{caption.strip()}\nBy: [{name}]({DEEPLINK + link}) {gender}".strip(),
                       parse_mode="markdown", reply_markup=answer_btn(q_id, a_))

    bot.send_message(user_id, "When you finish previewing your answer press once submit!")
    start_message(msg)

@bot.callback_query_handler(func=lambda c: re.search("^(Send|Edit|Del)Answer", c.data), joined=True, not_banned=True)
def send_answer(call: types.CallbackQuery):
    user_id = call.message.chat.id
    umsg_id = call.message.message_id
    q_id = (call.data.split("_")[1])
    ans_id = int(call.data.split("_")[2])
    with bot.retrieve_data(user_id) as data:
        is_reply = data.get('on_reply')

    if not is_reply:
        cur.execute("SELECT asker_id FROM Questions WHERE question_id = %s", (q_id,))
        user = cur.fetchone()[0]
        msg_id = None
    else:
        user = is_reply['user_id']
        msg_id = is_reply['msg_id'] 
    if call.data == f"SendAnswer_{q_id}_{ans_id}":
        cur.execute('update Answers set time = %s where answer_id = %s', (time(), ans_id))
        conn.commit()
        bot.copy_message(user_id, user_id, umsg_id, parse_mode='Markdown', 
            reply_markup=on_answer(user_id, q_id, ans_id),
            reply_to_message_id=msg_id)
        try:
            cur.execute("select channels from bot_setting")
            channels = json.loads(cur.fetchone()[0])
            
            for key, val in channels.items():
                if val.get('approve'):
                    ch_u = bot.get_chat(key).username
                    break
            else:return
            cur.execute('update Questions set browse = browse + 1 where question_id = %s', (q_id,))
            conn.commit()
            cur.execute('select message_id, browse from Questions where question_id = %s', (q_id,))
            msg_id, br = cur.fetchone()
            btn = types.InlineKeyboardMarkup()
            cur.execute('select question_link, browse_link from Questions where question_id = %s', (q_id,))
            ql, bl = cur.fetchone()
            btn.add(
                types.InlineKeyboardButton("Answer", url=DEEPLINK+ql),
                types.InlineKeyboardButton(f"Browse ({br})", url=DEEPLINK+bl)
            )
            try:
                bot.edit_message_reply_markup(f"@{ch_u}", int(msg_id), reply_markup=btn)
            except:
                pass

            username = 'https://t.me/{0}/{1}'.format(ch_u, msg_id)

            if not is_reply:
                bot.send_message(user, f"🔂 You have one new answer for [your question]({username})",
                                    parse_mode='markdown', disable_web_page_preview=True)
            bot.copy_message(user, user_id, umsg_id, parse_mode='Markdown', 
            reply_markup=on_answer(user_id, q_id, ans_id))
            bot.delete_message(user_id, umsg_id)
        except ApiTelegramException:
            pass
        
    elif call.data == f"EditAnswer_{q_id}_{ans_id}":
        cur.execute("SELECT lang FROM students WHERE user_id = %s", (call.from_user.id,))
        lang = cur.fetchone()[0]
        cur.execute("DELETE FROM Answers WHERE answer_id = %s", (ans_id,))
        conn.commit()
        bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)
        bot.send_message(call.from_user.id, "Send new your answer", reply_markup=cancel(lang))
        bot.set_state(call.from_user.id, Answer.answer)
    else:
        cur.execute("DELETE FROM Answers WHERE answer_id = %s", (ans_id,))
        conn.commit()
        start_message(call.message)

@bot.callback_query_handler(func=lambda call: re.match(r'^areply', call.data))
def reply_to_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Send your reply through text, voice or Media (Photo, Video)")
    bot.set_state(call.message.chat.id, Answer.answer)
    with bot.retrieve_data(call.message.chat.id) as data:
        data['on_reply'] = {'user_id':call.data.split(":")[1] , 'to_id': call.data.split(':')[3], 
        'question_id': call.data.split(":")[2], 'msg_id': call.message.message_id}

@bot.callback_query_handler(func=lambda call: call.data in ['edus', 'edut', 'edutref'], joined=True, not_banned=True)
def answer_books(call):
    bot.answer_callback_query(call.id)
    lang = user_lang(call.from_user.id)

    if call.data == call.data:
        if lang == 'am':
            text = "የክፍል ደረጃዎን ይምረጡ"
        else:
            text = "Select Your Grade"
        bot.edit_message_text(text, call.from_user.id, call.message.id, reply_markup=grade(lang, call.data))


@bot.callback_query_handler(func=lambda c: c.data == 'backgrade', joined=True, not_banned=True)
def back_grade(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    lang = user_lang(user_id)
    if lang == 'en':
        back = "<i>Select Book Type</i>"
    else:
        back = "<i>የመጽሃፍ አይነት ይምረጡ</i>"
    bot.edit_message_text(back, call.from_user.id, call.message.message_id,
                          parse_mode='HTMl', reply_markup=types_book_am())

@bot.callback_query_handler(func=lambda call: re.match(r"^grade", call.data))
def get_books(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    gr = call.data.split("_")[1]
    typ = call.data.split("_")[2]

    if typ == "edus":
        typ = "student"
    elif typ == "edut":
        typ = "teacher"
    else:
        typ = 'reference'
    text, btn = info_book(call, gr, typ)
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=btn)

def info_book(call, gr, typ):
    cur.execute("SELECT subject, balance, msg_id FROM books WHERE grade = %s AND type = %s", (gr, typ))
    catch = cur.fetchall()
    if  catch != (None):
        result = ""
        for i, v, m in catch:
            if m != 0:
                if v == 0:
                    result+=i+": Free\n"
                elif v >=1:
                    result+=f"{i}: {v} coin\n"
            else:
                result+=f'{i}: Not found!\n'
    else:
        result = """All book Coomingsoon !!"""
    lang = user_lang(call.from_user.id)
    if call.data == call.data:
        if lang == "am":
            text = 'መጽሃፍ ይምረጡ'
        else:
            text = "Chose book"
        text+='\n'+result
    lang = user_lang(call.message.chat.id)
    return text, books_btn(lang, typ, gr)

@bot.callback_query_handler(func=lambda call: re.match(r"book", call.data))
def on_get_books(call: types.CallbackQuery):
    subject = call.data.split(":")[1]
    cur = conn.cursor()
    lang = user_lang(call.message.chat.id)
    if not subject in ['back', 'main']:
        bk = call.data.split(":")[2]
        gr = call.data.split(":")[3]
        cur.execute("SELECT msg_id, balance, subject FROM books WHERE grade = %s AND type = %s AND subject = %s", (gr, bk, subject))
        u = cur.fetchone()
        exist = None if u in [None, (None,)] else u
        
        if call.message.chat.id == creator_id():
            bot.answer_callback_query(call.id)
            msg_id, bl, sub = exist
            cur.execute('select id from books where type = %s AND subject = %s AND grade = %s', (bk, subject, gr))
            bi = cur.fetchone()[0]
            if bi is None:return
            btn = on_book_click(bi, msg_id)
            if msg_id:
                text = f"""
                Subject: {sub}\nBalance: {bl}
                """
            else:
                text = f"Subject : {sub}"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=btn)
        
        msg_id, bl, sub = exist
        if  msg_id:
            try:
                cur.execute("SELECT balance FROM students WHERE user_id = %s", (call.from_user.id,))
                ub = cur.fetchone()[0]
                
                if not call.message.chat.id == creator_id():
                    
                    if not bl:
                        bot.answer_callback_query(call.id)
                        bot.copy_message(call.message.chat.id, CHANNEL_ID, msg_id)
                    
                    elif ub >= bl:
                        bot.answer_callback_query(call.id)
                        cur.execute("update students set balance  = balance - %s where user_id = %s", (bl, call.message.chat.id))
                        conn.commit()
                        bot.copy_message(call.message.chat.id, CHANNEL_ID, msg_id)
                        
                    else:
                        bot.answer_callback_query(call.id, "Your balance is insuficient", show_alert=True)

                else:
                    bot.answer_callback_query(call.id)
                    bot.copy_message(call.message.chat.id, CHANNEL_ID, msg_id)
            except Exception as e:
                bot.answer_callback_query(call.id, e.args[0], show_alert=True)
        else:
            bot.answer_callback_query(call.id, "This book is not available", show_alert=True)

    elif subject == 'back':
        bk = call.data.split(":")[2]
        if call.data == call.data:
            if lang == 'am':
                text = "የክፍል ደረጃዎን ይምረጡ"
            else:
                text = "Select Your Grade"
            bot.edit_message_text(text, call.from_user.id, call.message.id, reply_markup=grade(lang, bk))
    else:
        if lang == 'am':
            text = "_የመጽሃፍ አይነት ይምረጡ_"
        else:
            text = "_Select book type_"
        bot.edit_message_text(text, call.from_user.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=types_book_am())
class OnBook(StatesGroup):
    bal = State()
    add = State()

@bot.callback_query_handler(func=lambda call: re.match(r"ubook", call.data))
def on_book_setting(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bk, cmd, bi = call.data.split(":")
    cur.execute('select grade from books where id = %s ', (bi,))
    gr = cur.fetchone()[0]
    cur.execute('select subject, type from books where id = %s', (bi,))
    sub, ty = cur.fetchone()
    if cmd == 'dl':
        cur.execute("update books set msg_id = '0' where id = %s", (bi,))
        conn.commit()
        text, btn = info_book(call, gr, ty)
        bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=btn)        
    
    elif cmd == 'back':
        text, btn = info_book(call, gr, ty)
        bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=btn)    
    
    elif cmd == 'add':
        bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Forward the book")
        bot.set_state(call.message.chat.id, OnBook.add)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['book_id'] = bi
    
    elif cmd == 'bl':
        bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Enter Balance")
        bot.set_state(call.message.chat.id, OnBook.bal)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['book_id'] = bi

@bot.message_handler(state=OnBook.add, content_types=['document'], is_forwarded=True)
def add_book(msg: types.Message):
    msg_id = msg.forward_from_message_id
    with bot.retrieve_data(msg.chat.id) as data:
        kw = data['book_id']
    cur.execute("UPDATE books set msg_id = %s WHERE id = %s", (msg_id, kw))
    conn.commit()
    bot.send_message(msg.chat.id, "Book Added ")
    cur.execute('select type, subject, grade, balance from books where id = %s', (kw,))
    ty, sub, gr, bl = cur.fetchone()
    btn = on_book_click(kw, msg_id)
    text = f"""
        Subject: {sub}\nBalance: {bl}
        """
    bot.send_message(msg.chat.id, text, reply_markup=btn)

@bot.message_handler(state=OnBook.bal, is_digit=True)
def set_book_balance(msg: types.Message):
    balance = msg.text
    with bot.retrieve_data(msg.chat.id) as data:
        kw = data['book_id']
    cur.execute("UPDATE books set balance = %s WHERE id = %s", (balance, kw))
    conn.commit()
    bot.send_message(msg.chat.id, "Book Added ")
    cur.execute('select type, subject, grade, balance from books where id = %s', (kw,))
    ty, sub, gr, bl = cur.fetchone()
    btn = on_book_click(kw, True)
    text = f"""
        Subject: {sub}\nBalance: {bl}
        """
    bot.send_message(msg.chat.id, text, reply_markup=btn)
    

@bot.callback_query_handler(func=lambda call: call.data == 'withdr', joined=True, not_banned=True)
def withdraw_money(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    lang = user_lang(user_id)
    if lang == 'am':
        text = "ምን ያህል ብር ማዉጣት ይፈልጋሉ ?"
    else:
        text = "How many Birr do you want to Withdraw?"
    bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=amounts(lang))
        
@bot.callback_query_handler(func=lambda call: re.search('birr$|^backwithdr$', call.data), joined=True, not_banned=True)
def cashout_or_ignore(call):
    user_id = call.from_user.id
    cur = conn.cursor()
    cur.execute('select balance,lang,withdraw from students where user_id = %s', (user_id,))
    balance, lang, withdr = cur.fetchone()
    money = call.data.split('-')[0]
    money = ''.join(money)
    if call.data.endswith('birr'):
        if balance >= int(money):

            try:
                db.withdraw(user_id, money)
            except:
                raise

            if lang == 'en':
                bot.answer_callback_query(call.id, "We will send soon your withdrawal Money.")
            elif lang == 'am':
                bot.answer_callback_query(call.id, "ወጪ ያረጉትን ገንዘብ በ 24 ሰአት ጊዜ ውስጥ እንልክሎታለን።")

            start_message(call.message)
            cur.execute("""
SELECT first_name,user_id,phone_number, account_link,
lang, gender, balance FROM students WHERE user_id = %s""", (user_id,))
            first_name, ui, phone, acc_link, lang, gender, balance = cur.fetchone()
            if not gender:
                    gender = ''
            bot.send_message(creator_id(), f"""#Withdraw\n
<a href='{DEEPLINK+acc_link}'>{first_name}</a> {gender}
<b>ID</b> : <code>{ui}</code>
<b>Asked Balance</b> : {money}
<b>Current Balance</b>: {balance} 
<b>Phone Number</b>: {phone}""", parse_mode="HTML", reply_markup=question_btn(ui))
        else:
            if lang == 'en':
                bot.answer_callback_query(call.id, "Your balance is insufficent", show_alert=True)
            elif lang == 'am':
                bot.answer_callback_query(call.id, "ይቅርታ የጠየቁት ገንዘብ አሁን ካሎት ገንዘብ በላይ ነው ።", show_alert=True)
    else:
        cur.execute('select invitation_link,invites,balance, withdraw, bbalance from students join '
                           'bot_setting where user_id = %s', (user_id,))
        link, invites, balance, withdr, bbl = cur.fetchone()
        bot.edit_message_text(BalanceText[lang].format(balance, invites, withdr, bbl, DEEPLINK+link), user_id,
                                  call.message.message_id,
            parse_mode="HTML", reply_markup=withdraw(lang, DEEPLINK+link))

@bot.callback_query_handler(func=lambda call: call.data == 'bt', joined=True, not_banned=True)
def transfer_birr(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    lang = user_lang(user_id)
    if lang == 'en':
        text = bot.send_message(user_id, "Send reciever's ID", reply_markup=cancel('en'))
    else:
        text = bot.send_message(user_id, "የተቀባዩን መለያ ቁጥር ያስገቡ", reply_markup=cancel('am'))
    bot.register_next_step_handler(text, tr_money)

def tr_money(msg):
    user_id = msg.chat.id
    lang = user_lang(user_id)
    if msg.text.isdigit():
        r_id = msg.text
        all_btn = types.InlineKeyboardMarkup(row_width=3)
        _5 = types.InlineKeyboardButton("5 Birr", callback_data=f'tr-5_{r_id}')
        _10 = types.InlineKeyboardButton("10 Birr", callback_data=f'tr-10_{r_id}')
        _15 =types.InlineKeyboardButton("15 Birr", callback_data=f'tr-15_{r_id}')
        _20 = types.InlineKeyboardButton("20 Birr", callback_data=f'tr-20_{r_id}')
        _25 = types.InlineKeyboardButton("25 Birr", callback_data=f'tr-25_{r_id}')
        _50 = types.InlineKeyboardButton("50 Birr", callback_data=f'tr-50_{r_id}')
        _75 = types.InlineKeyboardButton("75 Birr", callback_data=f'tr-75_{r_id}')
        _100 = types.InlineKeyboardButton("100 Birr", callback_data=f'tr-100_{r_id}')
        all_btn.add(_5, _10, _15,_20, _25, _50, _75, _100)
        if lang == 'en':
            bot.send_message(user_id, "*How many birr do you want to Transfer?*",
                             reply_markup=all_btn, parse_mode="Markdown")
        elif lang == 'am':
            bot.send_message(user_id, "*ምን ያህል ብር ማስተላለፍ ይፈልጋሉ?*", reply_markup=all_btn, parse_mode="Markdown")
        start_message(msg)

    else:
        cancel_feedback(msg)

@bot.callback_query_handler(func=lambda call: re.search('^tr', call.data), joined=True, not_banned=True)
def transfer_birr_to_user(call):
    cur = conn.cursor()
    user_id = call.from_user.id
    r_id = call.data.split('_')[1]
    r_id = int(r_id)
    if db.user_is_not_exist(r_id):
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    cur.execute('select balance from students where user_id = %s', (user_id,))
    balance = cur.fetchone()[0]
    user_b = call.data.split('-')[1]
    user_b = ''.join(user_b).split('_')[0]
    user_b = int(user_b)

    if call.data == call.data:
        try:
            if balance >= user_b or user_id == creator_id():
                cur.execute('select lang from students where user_id = %s', (user_id,))
                lang = cur.fetchone()[0]
                if lang is not None:
                    try:
                        cur.execute('UPDATE students SET balance = balance + %s WHERE user_id = %s', (user_b, r_id,))
                        cur.execute('UPDATE students SET balance = balance - %s WHERE user_id = %s', (balance, user_id,))
                        conn.commit()
                        bot.answer_callback_query(call.id, "Transfer Done!")
                        try:
                            bot.delete_message(user_id, call.message.id)
                            start_message(call.message)
                        except Exception as e:
                            logging.exception(e)
                        user = bot.get_chat(user_id)
                        bot.send_message(user_id, "Transfer Done!")
                        bot.send_message(r_id, f"❇ You have recieved {user_b} Birr From {user.first_name}")
                    except Exception as e:
                            logging.exception(e)
            else:
                bot.answer_callback_query(call.id, 'Sorry balance is insuficient.', show_alert=True)
                start_message(call.message)

        except Exception as e:
            bot.send_message(user_id, "_No User found with {}_".format(r_id), parse_mode="Markdown")
            start_message(call.message)
        return

@bot.callback_query_handler(func=lambda call: call.data == 'bonus', joined=True, not_banned=True)
def recieve_bonus(call):
    data = {}
    user_id = call.from_user.id
    randb = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.9]
    amount = random.choice(randb)
    cur = conn.cursor()
    if not os.path.exists("bonus.text"):
        with open('bonus.text', 'w') as file:
            data[user_id] = {'amount': amount, 'time': time()}
            cur.execute("update students set balance = balance + %s where user_id = %s", (amount, user_id,))
            conn.commit()
            json.dump(data, file, indent=2)
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, "You have recieved {} Birr bonus!".format(amount))

    else:
        with open('bonus.text') as f:
            data = json.loads(f.read())
            if not str(user_id) in data:
                data[user_id] = {'amount':amount,'time':time()}
                cur.execute("update students set balance = balance + %s where user_id = %s", (amount, user_id,))
                conn.commit()
                with open('bonus.text', 'w') as file:
                    json.dump(data, file, indent=2)
                    bot.answer_callback_query(call.id)
                    bot.send_message(user_id, "You have recieved {} Birr bonus!".format(amount))
                
            else:
                clock = time()-data[str(user_id)]['time']
                if int(clock) // 60 // 60 >= 24:
                    data[user_id] = {'amount': amount, 'time': time()}
                    cur.execute("update students set balance = balance + %s where user_id = %s", (amount, user_id,))
                    conn.commit()
                    with open('bonus.text', 'w') as file:
                        json.dump(data, file, indent=2)
                        bot.answer_callback_query(call.id)
                        bot.send_message(user_id, "You have recieved {} Birr bonus!".format(amount))
                else:
                    with open('bonus.text') as file:
                        data = json.load(file)
                    bot.answer_callback_query(call.id, f"You have already recieved {data[str(user_id)]['amount']} "
                                                       f"Birr last 24 Hours. \
at least you have to wait {24-int(clock)//60//60} hours! ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data in ['lang', 'editp', 'closeS'], joined=True, not_banned=True)
def usersetting(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    msg_id = call.message.message_id
    lang = user_lang(user_id)
    if call.data == 'lang':
        bot.edit_message_text("_Select Language / ቋንቋ ይምረጡ_", user_id, msg_id, reply_markup=language_btn(),
                              parse_mode="Markdown")

    elif call.data == 'editp':
        if lang == 'am':
            bot.edit_message_text("መግለጫዎን ያድሱ", user_id, msg_id, reply_markup=edit_profile(user_id, lang))
        elif lang == 'en':
            bot.edit_message_text('Edit Your Profile', user_id, msg_id, reply_markup=edit_profile(user_id, lang))

    elif call.data == "closeS":
        bot.delete_message(user_id, call.message.id)
        start_message(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ['fname', '_username', 'gender', 'bio', 'back_edit'],
                            joined=True, not_banned=True)
def user_profile(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    bot.clear_step_handler_by_chat_id(user_id)
    lang = user_lang(user_id)
    cur = conn.cursor()
    if call.data == 'fname':
        fname = bot.send_message(user_id, "Enter your name\nNote that your name can only "
                                          "include latters and starts with capital latter!")
        bot.register_next_step_handler(fname, first_)

    elif call.data == '_username':
        fr = types.ForceReply()
        bot.send_message(user_id, "<b>Rule</b>\n a username\n1: must start with dollar ($) sign.\n"
                                  "example <code>$Abebe</code>\n"
                                "2: only include latters,numbers and underscore (_).\n"
                                "3: cannot start with numbers or underscore (_) and cannot end with underscore (_).\n"
                                "4: must be unique\n"
                                "5: after $ sign minimum length is 5!"
                                "6: is case insensetive ($username and $USERNAME are the same)", parse_mode="html")
        username = bot.send_message(user_id, "Enter new username", reply_markup=fr)
        bot.register_next_step_handler(username, username_)

    elif call.data == 'bio':
        bio = bot.send_message(user_id, "Write a few words about Your self.\n\nMaximun length is 75!")
        bot.register_next_step_handler(bio, bio_)

    elif call.data == 'gender':
        cur.execute('select gender from students where user_id = %s', (user_id,))
        gn = cur.fetchone()
        gender = None if gn == (None,) else gn[0]
        if lang == 'am':
            text = "ጾታ ይምረጡ"
        else:
            text = "Select Gender"
        bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=user_gender(lang, gender))

    else:
        cur.execute("SELECT first_name, joined_date, phone_number, "
            "lang, gender, username, bio FROM students WHERE user_id = %s", (user_id,))
        first_name, joined_date, phone, lang, gender, username, bio = cur.fetchone()
        bot.edit_message_text(SettingText.format(first_name, gender, phone, username, bio, tp(time(), joined_date)),
                              user_id, call.message.message_id, parse_mode="HTML", reply_markup=user_setting(lang))
        bot.clear_step_handler_by_chat_id(user_id)

def first_(msg):
    user_id = msg.chat.id
    first_name = msg.text

    lang = user_lang(user_id)
    if first_name.istitle() and first_name.isalpha():
        try:
            db.update_name(user_id, first_name)
        except:
            raise Exception("Something went wrong..")
        if lang == 'am':
            text = "መግለጫዎን ያድሱ"
        else:
            text = 'Edit Your Profile'
        bot.send_message(user_id, "Name updated!")
        bot.send_message(user_id, text, reply_markup=edit_profile(user_id, lang))
        bot.delete_message(user_id, msg.message_id - 2)
    else:
        bot.send_message(user_id, "Invalid name")

def username_(msg):
    user_id = msg.chat.id
    text = msg.text
    cur = conn.cursor()
    lang = user_lang(user_id)
    username = re.search(r'^\$[a-zA-Z]+_?[a-zA-Z0-9]+(_?[a-zA-Z0-9]+)*', text, re.I)

    if username:
        check = re.search(r'^\$(developer|admin|creator|owner)$', username.group(), re.I)

        if check and user_id != creator_id():
            bot.send_message(user_id, "This username has already taken.")
            fr = types.ForceReply()
            username=bot.send_message(user_id, "Enter new username", reply_markup=fr)
            bot.register_next_step_handler(username, username_)

        else:
            if len(username.group()) < 6:
                username = bot.send_message(user_id, "This username is too short")
                bot.register_next_step_handler(username, username_)
                return

            cur.execute("SELECT username FROM students")
            users = cur.fetchall()
            for i in users:
                if not i[0]: continue
                check = re.search(rf"\{username.group()}", i[0], re.IGNORECASE)
                if check:
                    bot.send_message(user_id, "This username is already taken.")
                    fr = types.ForceReply()
                    username = bot.send_message(user_id, "Enter new username", reply_markup=fr)
                    bot.register_next_step_handler(username, username_)
                    return
            else:
                try:
                    db.update_username(user_id, username.group())
                    if lang == 'am':
                        text = "መግለጫዎን ያድሱ"
                    else:
                        text = 'Edit Your Profile'
                    bot.send_message(user_id, "Username updated!")
                    bot.send_message(user_id, text, reply_markup=edit_profile(user_id, lang))
                    bot.delete_message(user_id, msg.message_id - 3)
                except:
                    raise

    else:
        bot.send_message(user_id, "Invalid username")

def bio_(msg):
    user_id = msg.chat.id
    user_bio = re.search(r'(.*){75}', msg.text, re.DOTALL)

    try:
        db.update_bio(user_id, user_bio.group())
    except:
        raise

    lang = user_lang(user_id)
    if lang == 'am':
        text = "መግለጫዎን ያድሱ"
    else:
        text = 'Edit Your Profile'
    bot.send_message(user_id, "Bio updated!")
    bot.send_message(user_id, text, reply_markup=edit_profile(user_id, lang))
    bot.delete_message(user_id, msg.message_id - 2)

@bot.callback_query_handler(func=lambda call: call.data in ['male', 'famale', 'back_gender', 'main_gender'],
                            joined=True, not_banned=True)
def gender_edit(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    lang = user_lang(user_id)
    if lang == 'am':
        text = "ጾታ ይምረጡ"
        textp = "መግለጫዎን ያድሱ"
    else:
        text = "Select Gender"
        textp = 'Edit Your Profile'
    kwargs = {"male" : '👨', 'famale' : "🧑" }
    if call.data in kwargs:
        try:
            gen = kwargs.get(call.data)

            db.update_gender(user_id, kwargs[call.data])
            bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=user_gender(lang, gen))
        except:
            raise
    elif call.data == 'back_gender':
        bot.edit_message_text(textp, user_id, call.message.message_id, reply_markup=edit_profile(user_id, lang))
    else:
        user_profile(call)

def user_not_joined():
    cur.execute("select channels from bot_setting")
    channels = json.loads(cur.fetchone()[0])
    text = ""
    _text = ""
    get = False
    cur.execute('select channels from bot_setting')
    channels:dict = json.loads(cur.fetchone()[0])
    for key, val in channels.items():
        if val.get('force_join'):
            text+="@"+bot.get_chat(int(key)).username+'\n'
            get = True
    if not get:return
    cur.execute('select user_id from students')
    users_id = cur.fetchall()
    get_u = False
    for user_id in users_id:
        for ch in text.split('\n'):
            try:
                user = bot.get_chat_member(ch, user_id[0])
                if not user.status in ['administrator', 'creator', 'member']:
                    _text += ch +'\n'
                    get_u = True
            except: continue 
        if get_u:
            try:
                bot.send_message(user_id[0], f"Dear user make shure that you joined our channel(s)\n{_text}") 
            except:continue
        get_u = False
        text = ""
    del text, _text, get, get_u

def show_account_info(msg, text):
    data = []

    cur.execute(
        "select first_name, user_id, joined_date, gender, username, bio, status from "
        "students where account_link = %s",
        (text,))
    data.extend(cur.fetchone())

    if not data[4]:
        data[4] = ''
    first_name, id, joined_date, gender, username, bio, status = data
    if status == 'banned':
        banned = True
    else:
        banned = False
    cur.execute("SELECT admins FROM bot_setting")
    if cur.fetchone():
        cur.execute("SELECT admins FROM bot_setting")
        admins = cur.fetchone()[0]
    else: admins = '{}'
    kwargs = json.loads(admins)
    if not id == msg.chat.id:
        bot.send_message(msg.chat.id, f"""\
<b> {first_name} </b> {gender}
--------------------------------------------
<b> Username </b>: {username}
<b> Bio </b>: <code> {bio} </code>\n
<i> Joined {tp(time(), joined_date)} ago </i >
---------------------------------------------
""", reply_markup=user_profile_info(id, banned=banned, admin_id=msg.from_user.id, **kwargs),
                         parse_mode="html")

def user_via_link(msg, text):
    if db.user_is_not_exist(msg.chat.id):
        cur.execute("SELECT first_name, gender FROM students "
                    "WHERE user_id = %s", (text,))

        first, gend = cur.fetchone()

        if not gend:
            gend = ''
        try:
            bot.send_message(msg.chat.id, f"You were invited by {first} {gend}")
            bot.send_message(text, f"User {util.user_link(msg.from_user)} was Joined by your invitational link",
                             parse_mode='html')
        except ApiTelegramException:
            pass
        finally:
            db.update_invite(text, msg.chat.id)
            start_message(msg)

    else:
        start_message(msg)


def show_questions(user_id, lang):
    showed = False
    count = 0
    cur.execute("""
        SELECT students.first_name, students.gender,students.account_link, 
        Questions.question,Questions.browse,Questions.type_q,
        Questions.caption, Questions.time, Questions.browse_link, 
        Questions.subject, Questions.status, Questions.question_id FROM students 
        JOIN Questions ON students.user_id = Questions.asker_id
        WHERE students.user_id = %s
        """, (user_id,))
    for ui in  cur.fetchall():
        first_name, gender, acc, q, b, tq, c, t, bl, sub, stat, q_id = ui
        btn = types.InlineKeyboardMarkup()
        burl = types.InlineKeyboardButton(f"Browse ({b})", url=DEEPLINK + bl)
        btn.add(burl)
        if stat == 'pending':
            br = on_user_question('pending', q_id)
        elif stat == "canceld":
            br = on_user_question('canceld', q_id)
        elif stat == 'preview':
            br = Panel(q_id)
        elif stat == 'declined':
            br = None
        else:
            br = btn
        showed = True
        try:
            if tq == "Text":
                bot.send_message(user_id, f"{sub}\n\n" + q + f"\n\nBy: [{first_name}]({DEEPLINK + acc}) {gender}",
                                 parse_mode="Markdown", reply_markup=br)
            elif tq == "Photo":
                bot.send_photo(user_id, q,
                               caption=f"{sub}\n\n" + c + f"\n\nBy: [{first_name}]({DEEPLINK + acc}) {gender}",
                               parse_mode="Markdown", reply_markup=br)
            elif tq == "Video":
                bot.send_video(user_id, q,
                               caption=f"{sub}\n\n" + c + f"\n\nBy: [{first_name}]({DEEPLINK + acc}) {gender}",
                               parse_mode="Markdown", reply_markup=br)
            else:
                bot.send_voice(user_id, q,
                               caption=f"{sub}\n\n" + c.strip() + f"\n\nBy: [{first_name}]({DEEPLINK + acc}) {gender}",
                               parse_mode="Markdown", reply_markup=br)    
        except:
            continue

    if not showed:
        ask_q = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Ask" if lang == 'en' else 'ጠይቅ', callback_data='ask_question')
        ask_q.add(btn)
        if lang == 'en':
            bot.send_message(user_id, "Sorry you don't have any asked question yet.", reply_markup=ask_q)
        elif lang == 'am':
            bot.send_message(user_id, "ይቅርታ እስካሁን ምንም የጠየቁት ጥያቄ የለም ።", reply_markup=ask_q)

def browse(msg, ids):
    user_id = ids
    print(user_id, msg)
    data = []
    ujson_msg_id = {}
    if is_verified(msg.chat.id):
        showed = False
        cur.execute("""
                SELECT Questions.question,Questions.type_q,Questions.caption,Questions.subject,
                students.first_name ,students.gender, students.account_link FROM students JOIN Questions ON 
                Questions.asker_id = students.user_id WHERE Questions.question_id = %s
                """, (ids,))
        for ui in cur.fetchall():
            data.extend(ui)
            if not data[6]:
                data[6] = ""
        print(data)
        q, tq, c, sub, first, gend, acc = data
        data.clear()
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("Answer", callback_data=f"answer_{ids}"))
        if tq == 'Text':
            bot.send_message(msg.chat.id, f'{sub}\n\n*{q}*\n\nBy: [{first}]({DEEPLINK + acc}) {gend}', reply_markup=btn,
                             parse_mode="Markdown")
        elif tq == "Photo":
            bot.send_photo(msg.chat.id, q,
                           caption=f"{sub}\n\n" + c + f"\n\nBy: [{first}]({DEEPLINK + acc}) {gend}",
                           parse_mode="Markdown", reply_markup=btn)
        elif tq == "Video":
            bot.send_video(msg.chat.id, q,
                           caption=f"{subj}\n\n" + c + f"\n\nBy: [{first}]({DEEPLINK + acc}) {gend}",
                           parse_mode="Markdown", reply_markup=btn)
        else:
            bot.send_voice(msg.chat.id, q,
                           caption=f"{subj}\n\n" + c.strip() + f"\n\nBy: [{first}]({DEEPLINK + acc}) {gend}",
                           parse_mode="Markdown", reply_markup=btn)
        cur.execute("""
                SELECT students.first_name, students.user_id, students.gender,students.account_link,
                Answers.answer, Answers.type_ans, Answers.caption, Answers.reply_to, Questions.question_id,
                Answers.answer_id FROM students JOIN Answers JOIN Questions ON students.user_id = Answers.user_id AND 
                Questions.question_id = Answers.question_id WHERE Questions.question_id = %s""", (ids,))
        for d in cur.fetchall():
            data.extend(d)
            first, ui, gend, acc, ans, ta, c, ar, q_id, ans_id = data
            reply = ujson_msg_id.get(ar)
            if not gend:
                gend = ""
            try:

                if ta == "Text":
                    m = bot.send_message(msg.chat.id, f"*{ans}*\n\nFrom: [{first}]({DEEPLINK + acc}) {gend}",
                                    parse_mode="Markdown", reply_markup=on_answer(ui, q_id, ans_id), reply_to_message_id=reply)
                elif ta == "Photo":
                    m = bot.send_photo(msg.chat.id, ans,
                                   caption=f"{c}\n\nFrom: [{first}]({DEEPLINK + acc}) {gend}",
                                   parse_mode="Markdown", reply_markup=on_answer(ui, q_id, ans_id), reply_to_message_id=reply)
                elif ta == "Video":
                    m = bot.send_video(msg.chat.id, ans,
                                   caption=f"{c}\n\nFrom: [{first}]({DEEPLINK + acc}) {gend}",
                                   parse_mode="Markdown", reply_markup=on_answer(ui, q_id, ans_id), reply_to_message_id=reply)
                else:
                    m = bot.send_voice(msg.chat.id, ans,
                                   caption=c.strip() + f"\nFrom: [{first}]({DEEPLINK + acc}) {gend}",
                                   parse_mode="Markdown",reply_markup=on_answer(ui, q_id, ans_id), reply_to_message_id=reply)

                ujson_msg_id[ans_id] = m.message_id
            except Exception:
                continue

            finally:
                showed = True
                data.clear()
            
        if not showed:
            bot.send_message(msg.chat.id, "Be the first to answer!")


def send_to_users(call: types.CallbackQuery):
    cur.execute("SELECT user_id FROm students")
    users_id = cur.fetchall()
    user_id = [ui for user_id in users_id for ui in user_id]
    try:
        del markups['☑ Done']
        del markups['➕ Add']
    except:pass
    for ui in user_id:
        try:
            bot.copy_message(ui, call.message.chat.id, call.message.message_id, 
                    reply_markup=util.quick_markup(markups),
            parse_mode='html')
        except Exception as e:
            continue

def forever():
    schedule.every(12).hours.do(user_not_joined)
    while 1:
        schedule.run_pending()

def main():
    bot.add_custom_filter(ChatFilter())
    bot.add_custom_filter(IsDigitFilter())
    bot.add_custom_filter(IsNumberFilter())
    bot.add_custom_filter(StateFilter(bot))
    bot.add_custom_filter(NotBannedFilter())
    bot.add_custom_filter(ForwardFilter())
    bot.add_custom_filter(IsAdminfilter())
    bot.add_custom_filter(FromUserFlter())
    bot.add_custom_filter(TextMatchFilter())
    bot.add_custom_filter(IsDeeplinkFilter())
    bot.add_custom_filter(UserJoinedChannelsFilter(bot))
    bot.enable_saving_states()
    t1 = threading.Thread(target=forever)
    t1.start()
    bot.infinity_polling()
  
if __name__ == "__main__": 
    while 1: 
        try:print("Poling started");main()
        except Exception as e:print(e)
    print("Stopped")

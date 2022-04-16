
BalanceText = {
"am":
"""
💰 <b>ቀሪ ሂሳብ</b> : {}
💳 <b>አጥቃላይ ወጪ</b> : {}
👥 <b>የጋበዙት ሰው</b> : {}
-------------------------------

👤 1 ሰዉ ⇛ {} ብር 💵

<b>የ መጋበዣ ሊንክ</b> : <code>{}</code>
-------------------------------

Take a bonus from 0 - 1 randomly; every 24 hours!
""",


"en":
"""
💰 <b>Current Balance</b> : {}
💳 <b>Total withdraw</b> : {}
👥 <b>Invites</b> : {}
-------------------------------------

👤 1 person ⇛ {} Birr 💵

<b>Invitation link</b> : <code>{}</code>
-------------------------------------

Take a bonus from 0 - 1 randomly; every 24 hours!
"""
}

SettingText = """<b> {} </b> {}
--------------------------------------------\n
<b> Phone Number </b>: <code>{}</code>
<b> Username </b>: <code>{}</code>
<b> Bio </b>: <code> {} </code>\n
--------------------------------------------
<i> Joined {} ago </i >
"""

CHANNEL = """📣 <b>Channels</b>\n
✳ From this menu you can add or remove channel.\n
✅ You can also give permissions for your bot wich what the bot can do on these channel.\n
🔧 Current channels:\n{}
"""

ADD_CHANNEL = """➕ <b>Add new Channel</b>\n
ℹ Forward here any message from you want to add as a channel.
"""

ADMIN = """🛃 <b>Manage Admins</b>\n
🔧 You are in the Bot Admin Settings mode.\n
⛑ Current admins:\n{}
"""

ADD_ADMIN = """🛠 <b>Adding new Admin</b>\n
ℹ Forward here any message from you want to add as an admin. 
"""
'''
str(user.id):{"send_message":False, 'approve_questions': False, 'manage_setting':False, 'ban_user':False,
                          'feedback':False, 'can_see':False}
        })'''

CHANNELP = """🔧 Manage bot's permission what it can do on the channel.\n
📣 channel :  {}\n
◽ approve questions: {}
◽ force join: {}
◽ send message : {}

"""

ADMINP = """🔧 Manage admin's permision\n
⛑ admin: {}\n
◽ see profile : {}
◽ ban user : {}
◽ feedback: {}
◽ send message: {}
◽ manage setting : {}
◽ approve questions : {}
"""

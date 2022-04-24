from mysql import connector
import os

def connection():
    conn = connector.connect(
            host=os.getenv('host'),
            password=os.getenv('pwd'),
            user=os.get('user'),
            database=os.get('database'),
            port=6201
        )
    cur = conn.cursor(buffered=True)
    try:
        conn.connect()
        conn.autocommit = True
    except:
        conn.reconnect()
    finally:
        return conn, cur

class PrivateDatabase:
    def __init__(self):
        self.conn, self.cur = connection()
        self.cur = self.conn.cursor()
        self.cur.execute("Select id from books")
        bi = self.cur.fetchone()
        sub = ['math', 'physics', 'chemistry', 'biology', 'civics', 'geography', 'ict',  'hpe',  'history', 'english', 'amharic',]
        if bi is None:
            for grade in range(7, 13):
                for s in sub:
                    for i in ['student', 'teacher', 'reference']:
                        self.cur.execute('insert into books(grade, type, subject, balance, msg_id) values(%s, %s, %s, %s, %s)', 
                        (grade, i, s, 0, 0))
                        self.conn.commit()
                        
                
    def user_is_not_exist(self, user_id):
        self.cur.execute("SELECT user_id FROM students")

        if not user_id in [i for j in self.cur.fetchall() for i in j]:
                return True
        else:
            return False 

    def save_data(self, first_name, user_id, date,
                link, balance, lang,
                acc_lick, is_ver, status):
        list = [first_name, user_id, date, link, 0, balance, lang, acc_lick, is_ver, 0, '', 'No bio yet', status]

        self.cur.execute('''    
            INSERT INTO students(
            first_name, 
            user_id,
            joined_date,
            invitation_link, 
            invites,
            balance,
            lang,
            account_link,
            is_verified, 
            withdraw,
            gender, 
            bio,
            status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', list)
        self.conn.commit()

    def update_lang(self, lang, user_id):
        self.cur.execute("""UPDATE students SET lang = %s WHERE user_id = %s""", (lang, user_id))
        self.conn.commit()

    def update_name(self, user_id, first_name):
        cur = self.conn.cursor()
        cur.execute("UPDATE students SET first_name = %s WHERE user_id = %s", (first_name, user_id,))
        self.conn.commit()

    def update_username(self, user_id, username):
        cur = self.conn.cursor()
        cur.execute("UPDATE students SET username = %s WHERE user_id = %s", (username, user_id,))
        self.conn.commit()

    def update_gender(self, user_id, gender):
        cur = self.conn.cursor()
        cur.execute("UPDATE students SET gender = %s  WHERE user_id = %s", (gender, user_id))
        self.conn.commit()

    def update_phone(self, user_id, phone):
        try:
            self.cur.execute("UPDATE students SET phone_number = %s  WHERE user_id = %s", (phone, user_id))
        except Exception as e:
            print(e)
            self.cur.execute('delete from students where phone_number = %s', (phone,))
            self.cur.execute("UPDATE students SET phone_number = %s  WHERE user_id = %s", (phone, user_id))
        finally:
            self.conn.commit()

    def update_bio(self, user_id, bio):
        cur = self.conn.cursor()
        cur.execute('UPDATE students SET bio = %s WHERE user_id = %s', (bio, user_id,))
        self.conn.commit()

    def save_question(self, user_id, text, typ, subj,  q_link, b_link, caption=""):
        from time import  time
        self.cur.execute("""INSERT INTO Questions(asker_id, question, time, type_q, status, subject, question_link, 
        browse_link, browse, caption) VALUES(%s , %s, %s, %s, %s, %s, %s, %s, 0, %s)""",
                     (user_id, text, time(), typ, 'preview', subj, q_link, b_link, caption))
        self.conn.commit()


    def update_bot_balance(self, balance):
        self.cur.execute("UPDATE bot_setting SET bbalance = %s", (balance,))
        self.conn.commit()

    def update_balance(self, user_id, balance):
        self.cur.execute("UPDATE students SET balance = balance + %s WHERE user_id = %s", (balance, user_id))
        self.conn.commit()

    def update_invite(self, inviter_id, invited_id):
        self.cur.execute("INSERT INTO invites VALUES(%s, %s, %s)", (inviter_id, invited_id, 0))
        self.cur.execute("UPDATE students SET invites = invites + 1 WHERE user_id =  %s", (inviter_id,))
        self.conn.commit()

    def ban_user(self, user_id):
        self.cur.execute("UPDATE students SET status = 'banned' WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def unban_user(self, user_id):
        self.cur.execute("UPDATE students SET status = 'member' WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def set_verifie(self, user_id):
        self.cur.execute("UPDATE students SET is_verified = 'True' WHERE user_id = %s", (user_id,))
        self.conn.commit()
        self.cur.execute("SELECT user_id FROM invites")
        i = self.cur.fetchall()
        if (user_id,) in [j for j in i]:
            
            self.cur.execute("SELECT bbalance, inviter_id FROM bot_setting JOIN invites WHERE user_id = %s", (user_id,))
            u = self.cur.fetchone()
            self.cur.execute("UPDATE students SET balance = balance + %s WHERE user_id = %s", u)
            self.conn.commit()

    def insert_answer(self, user_id, q_id, ans, typ, a_link, caption, reply_to=0):
        from time import time
        self.cur.execute(
            "INSERT INTO Answers(user_id, question_id, answer, type_ans, time, answer_link, status, caption, reply_to) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                user_id, q_id, ans, typ, time(), a_link, 'preview', caption, reply_to
            ))
        self.conn.commit()

    def withdraw(self, user_id, amount):
        self.cur.execute('update students set balance = balance - %s where user_id = %s', (amount, user_id))
        self.cur.execute('update students set withdraw = withdraw +  %s where user_id = %s', (amount, user_id))
        self.conn.commit()


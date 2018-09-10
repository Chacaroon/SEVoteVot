# coding=utf-8
import telebot
import db.index
from db.models.vote_model import Vote
import re
import logging

bot = telebot.TeleBot("694338190:AAGcL2_b_SMxSxooMCDxw5anK_2j0-5iFus", threaded=False)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, """
Привет. Меня зовут Voter
Скажи /newvote и мы приступим к созданию голосования
""")


@bot.message_handler(commands=['newvote'])
def create_vote(message):
    if is_exist_vote_in_chat(message.chat.id):
        bot.send_message(message.chat.id, "В одном чате должно быть не больше одного голосования.\n"
                                          "Напишите /endvote, чтобы получить результат и завершить голосование")
        return

    bot.send_message(message.chat.id, "Для начала укажи тему голосования\n"
                                      "Чтобы указать тему голосования, напишите /addtheme <тема>")


@bot.message_handler(commands=['addtheme'])
def add_title(message):
    if is_exist_vote_in_chat(message.chat.id):
        bot.send_message(message.chat.id, "Тема голосования уже установлена")
        return

    theme = re.split('/addtheme', message.text)[1]
    if not theme:
        bot.send_message(message.chat.id, "Тема не может быть пустой")
        return

    theme = re.sub("^\s+|\s+$", "", theme, flags=re.UNICODE)

    add_vote_to_database(author=message.from_user.username, chat_id=message.chat.id, title=theme)

    bot.send_message(message.chat.id, "Добавьте первый вариант.\n"
                                      "Чтобы это сделать, воспользуйтесь командой /addcase <вариант>")


def add_vote_to_database(author, chat_id, title):
    vote = Vote(author=author, chat_id=chat_id, title=title)

    vote.save()


@bot.message_handler(commands=['addcase'])
def add_case(message):
    if not is_exist_vote_in_chat(message.chat.id):
        in_the_chat_there_is_no_vote(message.chat.id)
        return

    case = re.split('/addcase', message.text)[1]
    if not case:
        bot.send_message(message.chat.id, "Вариант не может быть пустым")
        return

    case = re.sub("^\s+|\s+$", "", case, flags=re.UNICODE)

    get_vote_by_chat_id(message.chat.id, False).update({
        "$push": {"cases": {"case": case, "count": 0}}
    })

    bot.send_message(message.chat.id, "Добавьте ещё один вариант или напишите /done чтобы завершить создание опроса")


@bot.message_handler(commands=["done", "vote"])
def complete_vote_creating(message):
    if not is_exist_vote_in_chat(message.chat.id):
        in_the_chat_there_is_no_vote(message.chat.id)
        return

    bot.send_message(message.chat.id, generate_vote_form(message.chat.id))


def generate_vote_form(chat_id):
    vote = get_vote_by_chat_id(chat_id, False)[0]

    result = ""

    result += "Тема: {} \n\n".format(vote.title)

    i = 1
    for case in vote.cases:
        result += "/{}. {}\n".format(str(i), case["case"])
        i += 1

    result += "\nЧтобы снова вывести форму голосования, введите команду /vote" \
              "\nДля просмотра результата введите команду /result" \
              "\nДля завершения голосования введите команду /endvote"

    return result


@bot.message_handler(regexp="\/\d+")
def increase_case_count(message):
    if not is_exist_vote_in_chat(message.chat.id):
        in_the_chat_there_is_no_vote(message.chat.id)
        return

    if whether_the_user_voted(message.chat.id, message.from_user.username):
        bot.send_message(message.from_user.id, "Голосовать можно только один раз")
        return

    vote = get_vote_by_chat_id(message.chat.id, False)[0]

    case_number = int(re.search('/(\d+)(@.+)?', message.text).group(1)) - 1

    case = vote.cases[case_number]

    get_vote_by_chat_id(message.chat.id, False).update({
        "$inc": {
            "cases." + str(case_number) + ".count": 1
        },
        "$push": {"voted_users": message.from_user.username}
    })

    bot.send_message(message.chat.id, "@{} проголосовал за {}".format(message.from_user.username, case["case"]))


def whether_the_user_voted(chat_id, username):
    vote = get_vote_by_chat_id(chat_id, False)[0]

    return username in vote.voted_users


@bot.message_handler(commands=['result'])
def get_result(message):
    if not is_exist_vote_in_chat(message.chat.id):
        in_the_chat_there_is_no_vote(message.chat.id)
        return

    vote = get_vote_by_chat_id(chat_id=message.chat.id, is_completed=False)[0]

    result = generate_result(vote, True)

    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=["endvote"])
def end_vote(message):
    if not is_exist_vote_in_chat(message.chat.id):
        in_the_chat_there_is_no_vote(message.chat.id)
        return

    vote_to_update = get_vote_by_chat_id(chat_id=message.chat.id, is_completed=False)

    vote = vote_to_update[0]

    vote_to_update.update({
        "$set": {"is_completed": True}
    })

    result = generate_result(vote, False)

    bot.send_message(message.chat.id, result)


def generate_result(vote, in_process):
    result = "Тема {}\n\n".format(vote.title)

    i = 1
    for case in vote.cases:
        result += "{}. {}: {}\n".format(str(i), case["case"], str(case["count"]))
        i += 1

    result += "\nЧтобы снова вывести форму голосования, введите команду /vote" \
              "\nДля просмотра результата введите команду /result"

    if (in_process):
        result += "\nДля завершения голосовани введите команду /endvote"

    return result


def in_the_chat_there_is_no_vote(chat_id):
    bot.send_message(chat_id, "В чате нет активного голосования\n"
                              "Для созданя голосования введите команду /newvote")


def get_vote_by_chat_id(chat_id, is_completed):
    return Vote.objects.raw({"chat_id": chat_id, "is_completed": is_completed})


def is_exist_vote_in_chat(chat_id):
    votes_count = get_vote_by_chat_id(chat_id, False).count()

    return votes_count > 0


bot.polling()

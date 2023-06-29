#!/usr/bin/python3

"""
dependencies:
    pip3 install --upgrade python-telegram-bot

This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import os
import sys
import random as rnd
from threading import Thread

import telegram
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackQueryHandler, CallbackContext, \
    ConversationHandler
from telegram.utils.helpers import mention_html

from apis.tgram.utils import restricted, reply_func, admin_reply, set_bot
from config.common import deploy_server
from config.environments import get_bot_token, get_bot_url, get_pinned_message
from config.log_config import log_level, getLogger
from config.version import version
import datetime as dt
import dateutil.relativedelta as dtutil

ENTER_PRESENTATION_FILE = 0

# Enable logging
CAPTCHA_TIMEOUT_SECONDS = 60

CORRECT_ANSWERS = {
    "leche": "🥛",
    "vino": "🍷",
    "refresco": "🥤",
    "zumo": "🧃"
}

logger = getLogger(__name__)
updater = Updater(get_bot_token())

TEST_MESSAGE = 'Hola {}, necesitamos comprobar que no eres un bot, tienes 15s para elegir la bebida que hay en el menú.'
PINNED_MESSAGE = get_pinned_message()
WELCOME_MESSAGE = 'Has superado la prueba. Te damos la bienvenida, {}!!! \n' + PINNED_MESSAGE
BAN_MESSAGE = 'El usuario {} ha sido exiliado por no resolver el captcha a tiempo. Me he ganado un +1'


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    global updater


    # schedule_jobs(updater.job_queue)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler('help', show_help))
    dp.add_handler(CommandHandler('log', log, pass_args=True))
    dp.add_handler(CommandHandler('quit', quit_bot))
    dp.add_handler(CommandHandler('restart', restart))

    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,
                                  manage_new_member))

    dp.add_handler(CallbackQueryHandler(captcha_button_pressed))

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('addpresentations', ask_for_presentations),
        ],
        states={
            ENTER_PRESENTATION_FILE: [MessageHandler(Filters.chat_type.private & Filters.document, upload_document)],
        },
        fallbacks=[],
    )
    dp.add_handler(conv_handler)

    # dp.add_handler(MessageHandler(Filters.chat_type.private & Filters.document, upload_document))

    # log all errors
    dp.add_error_handler(error_handler)

    if deploy_server():
        PORT = int(os.environ.get('PORT', '8443'))  # Telegram supported without reverse proxy: 443, 80, 88 and 8443


        webhook_url = "https://{}.herokuapp.com/{}".format(get_bot_url(), get_bot_token())
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=get_bot_token(),
                              webhook_url=webhook_url)
    else:
        # Start the Bot
        updater.start_polling()  # XXX These are supposed to improve UX: poll_interval = 1.0,timeout=20

    set_bot(updater.bot)

    try:
        admin_reply('Bot iniciado')
    except Exception as e:
        logger.exception('Error when trying to notify the init completion')


    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def ask_for_presentations(update: Update, context: CallbackContext):
    context.bot.send_message(update.effective_chat.id, 'Envíe ahora al bot su fichero o sus ficheros de la presentación/charla')
    reply_keyboard = [
        [InlineKeyboardButton('FINALIZAR', callback_data='END_UPLOAD'),]
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    context.bot.send_message(update.effective_chat.id, 'O presione el botón para dar por finalizada la subida', reply_markup=reply_markup)
    return ENTER_PRESENTATION_FILE


def upload_document(update: Update, context: CallbackContext):
    if update.callback_query:
        if update.callback_query.data == 'END_UPLOAD':
            update.callback_query.answer('Subida de documentos finalizada')
            return ConversationHandler.END

    import io
    from github import Github


    g = Github(os.environ.get('GITHUB_TOKEN'))

    repo = g.get_repo('pythoncoruna/main')

    received_file: telegram.File = context.bot.get_file(update.message.document.file_id)
    content_stream = io.BytesIO()
    received_file.download(out=content_stream)
    try:
        content = content_stream.getvalue().decode('utf-8')
    except UnicodeDecodeError:
        content = content_stream.getvalue()
    path = f'resources/presentations/{update.message.document.file_name}'
    repo.create_file(path, f'Subida de {update.message.document.file_name}', content)

    try:
        update.callback_query.answer('Subiendo documento')
    except:
        pass

    return ENTER_PRESENTATION_FILE


def shutdown(update, context):
    """
    Shuts down the bot
    :param update: the update info from Telegram for this command
    :param context: the context
    """
    reply = reply_func(update)
    reply('Finalizando bot...')
    updater.stop()
    updater.is_idle = False
    reply('Bot apagado.')


@restricted(logger)
def quit_bot(update, context):
    """
    Quits this bot
    :param update: the update info from Telegram for this command
    :param context: the context
    """
    Thread(target=shutdown,
           args=(context.bot, update,)).start()
    import os
    import signal
    os.kill(os.getpid(), signal.SIGTERM)


def stop_and_restart():
    """
    Gracefully stops the Updater and replaces the current process with a new one
    """
    updater.stop()
    os.execl(sys.executable, sys.executable, *sys.argv)


@restricted(logger)
def restart(update, context):
    """
    Restarts the bot
    :param update: the update info from Telegram for this command
    :param context: the context
    """
    reply = reply_func(update)
    reply('Bot reiniciando...')
    Thread(target=stop_and_restart).start()


@restricted(logger)
def log(update, context):
    """
    Changes the log level to desired input value
    :param update: the update info from Telegram for this command
    :param context: the context
    """
    reply = reply_func(update)

    try:
        arg_list = []
        if len(context.args):
            new_log_level = int(context.args[0])
            arg_list.append(new_log_level)

        current_log_level = log_level(*arg_list)
        reply(f'Nivel de log: {current_log_level}')
    except ValueError:
        reply('Valor no válido')


def show_help(update, context):
    """
    Send a message when the command /help is issued.
    :param update: the update info from Telegram for this command
    :param context: the context
    """
    help_text = 'Bienvenido al bot de Telegram (*' + version() + '*) para administrar grupos.\n' \
                'Este bot creará un borrador de forma automática en blogger al introducir una URL seguida del título deseado\n' \
                '  /help - Muestra la ayuda\n' \
                '  /addpresentation - Sube documento relativo a unha charla/presentación\n' \
                '  /quit - Detiene completamente el bot\n' \
                '  /restart - Reinicia el bot\n'

    reply = reply_func(update)
    logger.info(f'Help request from chat id {update.effective_chat.id}')
    reply(help_text, parse_mode='Markdown')


def error_handler(update, context):
    """
    Logs errors caused by updates.
    Does not use @run_async for complicated reasons (ptb developer said)
    :param context: the context
    :param update: the update info from Telegram for this command
    """
    logger.warning('La actualización "%s" causó el error "%s"', update, context.error)


def manage_new_member(update: telegram.Update, context: telegram.ext.callbackcontext.CallbackContext):
    """
    Manages a new member in an bot-moderated-chat.

    :param context: the context
    :param update: the update info from Telegram for this command
    """
    member: telegram.User
    logger.info('New member detected')
    for member in update.effective_message.new_chat_members:
        if member.is_bot:
            context.bot.ban_chat_member(update.effective_chat.id, member.id, until_date=forever_dt())

        if context.bot.id != member.id:
            revoke_member_permissions(context, update, member)
            message = reply_captcha_to_user(update, member)

            captcha_args = {
                'kwargs': {
                    'member': member,
                    'chat_id': update.effective_chat.id,
                    'message': message
                }
            }
            context.job_queue.run_once(captcha_ban_if_timeout, CAPTCHA_TIMEOUT_SECONDS,
                                       name=str(member.id),
                                       job_kwargs=captcha_args)


def reply_captcha_to_user(update, member):
    reply = reply_func(update)
    markup = get_keyboard_markup(member)
    message = reply(TEST_MESSAGE.format(mention_html(member.id, member.first_name)), reply_markup=markup, parse_mode='HTML')
    return message


def revoke_member_permissions(context, update, member):
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False
    )
    context.bot.restrict_chat_member(
        int(update.effective_chat.id),
        member.id,
        permissions,
        until_date=forever_dt()
    )


def captcha_button_pressed(update: telegram.Update, context: telegram.ext.callbackcontext.CallbackContext):
    query = update.callback_query
    query_data = query.data.split(",", 2)
    drink_selected = query_data[0]
    str_id_who_entered_the_chat = query_data[1]
    id_who_entered_the_chat = int(str_id_who_entered_the_chat)

    person_name = query.data.split(",")[2]
    id_who_pressed_button = query.from_user.id

    if id_who_pressed_button == id_who_entered_the_chat:
        job_to_be_cancelled = None
        jobs_tuple = context.job_queue.get_jobs_by_name(str_id_who_entered_the_chat)
        try:
            job_to_be_cancelled = jobs_tuple[0]
        except IndexError:
            pass
        if drink_selected in CORRECT_ANSWERS.keys():
            if job_to_be_cancelled:
                job_to_be_cancelled.job.remove()
            grant_permissions_to_user(context, update, id_who_entered_the_chat)
            update.effective_chat.send_message(WELCOME_MESSAGE.format(person_name))
            context.bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
        else:
            query.edit_message_text(text=f"🚨 El usuario {person_name} es sospechoso y fue puesto en cuarentena! 🚨")
            if job_to_be_cancelled:
                job_to_be_cancelled.job.remove()


def grant_permissions_to_user(context, update, id_who_entered_the_chat):
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
    )
    context.bot.restrict_chat_member(
        int(update.effective_chat.id),
        id_who_entered_the_chat,
        permissions,
    )


def captcha_ban_if_timeout(context: telegram.ext.callbackcontext.CallbackContext, member: telegram.User, chat_id, message: telegram.Message):
    context.bot.ban_chat_member(chat_id, member.id, until_date=forever_dt())
    message.edit_text(BAN_MESSAGE.format(member.first_name), reply_markup=None)


def forever_dt():
    return dt.datetime.now() + dtutil.relativedelta(years=1, days=1)


def kick_dt():
    return dt.datetime.now() + dt.timedelta(seconds=32)


def get_keyboard_markup(member):
    keyboard_items = [
        InlineKeyboardButton("🥩", callback_data=f'bistec,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥝", callback_data=f'kiwi,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥓", callback_data=f'bacon,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥥", callback_data=f'coco,{member.id},{member.first_name}'),
        InlineKeyboardButton("🍩", callback_data=f'donut,{member.id},{member.first_name}'),
        InlineKeyboardButton("🌮", callback_data=f'taco,{member.id},{member.first_name}'),
        InlineKeyboardButton("🍕", callback_data=f'pizza,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥗", callback_data=f'ensalada,{member.id},{member.first_name}'),
        InlineKeyboardButton("🍌", callback_data=f'plátano,{member.id},{member.first_name}'),
        InlineKeyboardButton("🌰", callback_data=f'castaña,{member.id},{member.first_name}'),
        InlineKeyboardButton("🍭", callback_data=f'chupachups,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥑", callback_data=f'aguacate,{member.id},{member.first_name}'),
        InlineKeyboardButton("🍗", callback_data=f'pollo,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥪", callback_data=f'sandwich,{member.id},{member.first_name}'),
        InlineKeyboardButton("🥒", callback_data=f'pepino,{member.id},{member.first_name}'),
    ]

    solution_key, solution_emoji = rnd.choice(list(CORRECT_ANSWERS.items()))
    keyboard_items.append(InlineKeyboardButton(f"{solution_emoji}", callback_data=f'{solution_key},{member.id},{member.first_name}'))

    rnd.shuffle(keyboard_items)

    keyboard = []
    counter = 0
    NUM_FILAS = 4
    NUM_BOTONES = 4
    for i in range(NUM_FILAS):  # create a list of the rows contained in the keyboard
        row = []
        for n in range(NUM_BOTONES):
            keyboard_item = keyboard_items[counter]
            row.append(keyboard_item)  # fills nested lists with data
            counter += 1
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


if __name__ == '__main__':
    main()

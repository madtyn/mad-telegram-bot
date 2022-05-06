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
from random import shuffle
from threading import Thread

import telegram
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackQueryHandler

from apis.tgram.utils import restricted, reply_func, admin_reply, set_bot
from config.common import deploy_server
from config.environments import get_bot_token, get_bot_app_name
from config.log_config import log_level, getLogger
from config.version import version
import datetime as dt
import dateutil.relativedelta as dtutil

# Enable logging
CAPTCHA_TIMEOUT_SECONDS = 60

logger = getLogger(__name__)
updater = Updater(get_bot_token())

TEST_MESSAGE = 'Hola {}, necesitamos comprobar que no eres un bot, tienes 15 s para elegir la bebida que hay en el menú.'
WELCOME_MESSAGE = 'Has superado la prueba. Te damos la bienvenida, {}!!! \n' \
                  'Para cualquier duda mira el mensaje anclado, por favor:\n\thttps://t.me/magicarena/80123'
BAN_MESSAGE = 'El usuario {} ha sido exiliado por no resolver el captcha a tiempo. Me he ganado un +1'
MTG_CHAT_ID = -1001234452463


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

    dp.add_handler(CallbackQueryHandler(button_pressed))

    # log all errors
    dp.add_error_handler(error_handler)

    if deploy_server():
        PORT = int(os.environ.get('PORT', '8443'))  # Telegram supported without reverse proxy: 443, 80, 88 and 8443
        webhook_url = "https://{}.herokuapp.com/{}".format(get_bot_app_name(), get_bot_token())
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
            context.job_queue.run_once(captcha_timeout, CAPTCHA_TIMEOUT_SECONDS,
                                       name=str(member.id),
                                       job_kwargs=captcha_args)


def reply_captcha_to_user(update, member):
    reply = reply_func(update)
    markup = get_keyboard_markup(member)
    message = reply(TEST_MESSAGE.format(member.first_name), reply_markup=markup)
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


def button_pressed(update: telegram.Update, context: telegram.ext.callbackcontext.CallbackContext):
    query = update.callback_query
    str_id_who_entered_the_chat = query.data.split(",")[0]
    id_who_entered_the_chat = int(str_id_who_entered_the_chat)

    person_name = query.data.split(",")[1]
    id_who_pressed_button = query.from_user.id

    if id_who_pressed_button == id_who_entered_the_chat:
        job_to_be_cancelled = None
        jobs_tuple = context.job_queue.get_jobs_by_name(str_id_who_entered_the_chat)
        try:
            job_to_be_cancelled = jobs_tuple[0]
        except IndexError:
            pass
        if 'leche' in query.data:
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


def captcha_timeout(context: telegram.ext.callbackcontext.CallbackContext, member: telegram.User, chat_id, message: telegram.Message):
    context.bot.ban_chat_member(chat_id, member.id, until_date=forever_dt())
    message.edit_text(BAN_MESSAGE.format(member.first_name), reply_markup=None)


def forever_dt():
    return dt.datetime.now() + dtutil.relativedelta(years=1, days=1)


def kick_dt():
    return dt.datetime.now() + dt.timedelta(seconds=32)


def get_keyboard_markup(member):
    keyboard_items = [
        InlineKeyboardButton("🥩", callback_data=f'{member.id},{member.first_name},bistec'),
        InlineKeyboardButton("🥝", callback_data=f'{member.id},{member.first_name},kiwi'),
        InlineKeyboardButton("🥛", callback_data=f'{member.id},{member.first_name},leche'),
        InlineKeyboardButton("🥓", callback_data=f'{member.id},{member.first_name},bacon'),
        InlineKeyboardButton("🥥", callback_data=f'{member.id},{member.first_name},coco'),
        InlineKeyboardButton("🍩", callback_data=f'{member.id},{member.first_name},donut'),
        InlineKeyboardButton("🌮", callback_data=f'{member.id},{member.first_name},taco'),
        InlineKeyboardButton("🍕", callback_data=f'{member.id},{member.first_name},pizza'),
        InlineKeyboardButton("🥗", callback_data=f'{member.id},{member.first_name},ensalada'),
        InlineKeyboardButton("🍌", callback_data=f'{member.id},{member.first_name},plátano'),
        InlineKeyboardButton("🌰", callback_data=f'{member.id},{member.first_name},castaña'),
        InlineKeyboardButton("🍭", callback_data=f'{member.id},{member.first_name},chupachups'),
        InlineKeyboardButton("🥑", callback_data=f'{member.id},{member.first_name},aguacate'),
        InlineKeyboardButton("🍗", callback_data=f'{member.id},{member.first_name},pollo'),
        InlineKeyboardButton("🥪", callback_data=f'{member.id},{member.first_name},sandwich'),
        InlineKeyboardButton("🥒", callback_data=f'{member.id},{member.first_name},pepino')
    ]

    shuffle(keyboard_items)
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

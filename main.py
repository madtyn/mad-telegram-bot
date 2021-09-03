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
from threading import Thread

import telegram
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters

from apis.tgram.utils import restricted, reply_func, admin_reply, set_bot
from config.common import deploy_server
from config.environments import get_bot_token, get_bot_app_name
from config.log_config import log_level, getLogger
from config.version import version

# Enable logging

logger = getLogger(__name__)
updater = Updater(get_bot_token())


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


def manage_new_member(update: telegram.Message, context):
    """
    Manages a new member in an Alfred-moderated-chat.
    NOTE: Right now it only registers in database every new chat the bot enters in

    :param context: the context
    :param update: the update info from Telegram for this command
    """
    member: telegram.User
    for member in update.effective_message.new_chat_members:
        if context.bot.id != member.id:
            reply = reply_func(update)
            reply(f'Bienvenido {member.first_name}')


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

    # log all errors
    dp.add_error_handler(error_handler)

    if deploy_server():
        PORT = int(os.environ.get('PORT', '8443'))  # Telegram supported without reverse proxy: 443, 80, 88 and 8443
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=get_bot_token())
        updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(get_bot_app_name(), get_bot_token()))
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


if __name__ == '__main__':
    main()

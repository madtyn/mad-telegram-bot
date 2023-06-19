# mad-telegram-bot

## Configuration

There are config files at config/, one with common settings:
- common.py 


    COMMON_SETTINGS = {
        'LIST_OF_ADMINS': [<some_Telegram_numeric_id>, ],
        'PINNED_MESSAGE': 'https://t.me/<somegroup>/<some_message_id>',
    }

and one for each environment:
- dev_env.py
- pro_env.py

One will be selected depending on the value of ENV environment variable,
which can have value 'dev', or 'pro'. You can customize environments by taking a look at environments.py

Each one with following content, that can be customized:

    SETTINGS = {
        'HOST': '<some x.x.x.x IP or some mydomain.com>'
        'BOT_APP_NAME': '<some name for the Heroku url>', 
        'ADMIN_ID': <the telegram ID for the admin>,
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN'),
    }

- HOST: Some url or IP where the bot is hosted. Only needed on deployment
- BOT_APP_NAME: Only for Heroku deployment. Only needed on deployment
- ADMIN_ID: The telegram ID for the admin user
- TELEGRAM_BOT_TOKEN: The bot token from the godfather


<b>NOTE: Don't use HOST and BOT_APP_NAME at the same time. Use either one or the other</b>

## Deployment

git push production main:master

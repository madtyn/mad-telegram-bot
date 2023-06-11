import os

MARTIN = 13333606

COMMON_SETTINGS = {
    'LIST_OF_ADMINS': [MARTIN, ],
}


def get_active_env():
    """
    Returns the active environment name, which is the directory name as well
    :return: the active environment
    """
    return os.environ.get('ENV', 'dev')


def deploy_server():
    """
    Returns if this environment
    is remotely deployed on a server (eg. heroku)
    :return: True if deployed remotely, False otherwise
    """
    return get_active_env() in ('pro', 'sta')


def production():
    """
    Returns if this environment
    is production environment (eg. heroku)
    :return: True if production, False otherwise
    """
    return get_active_env() == 'pro'

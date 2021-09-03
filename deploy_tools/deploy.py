import os
import re
import sys

RC_INPUT_MSG = 'RC version? (0 => non-release-candidate, ' \
               'Enter =>  current one++): '

ROOT_PROJECT = os.path.dirname(os.path.dirname(__file__))
version_file_path = os.path.join(ROOT_PROJECT, 'config', 'version.py')
[MAJ, MIN, PATCH, RCV] = range(1, 5)
PATTERN = r'(\d+)\.(\d+)\.(\d+)(-rc(?P<rcv>\d+))?'
VERS_FILE = os.path.join(os.getcwd(), '..', 'config', 'version.py')
VERS_LINE = r"VERSION = '\d+\.\d+\.\d+(-rc\d+)?'"
BASIC_VER = '{}.{}.{}'
RELEASE_VER = '-rc{}'
CAND_VER = BASIC_VER + RELEASE_VER

TARGET_BRANCH_NAME = 'main'

def get_version_numbers(line):
    """
    Gets the version numbers as a list from a version string
    :param line: the line with the version
    :return: the version numbers list
    """
    result = []
    match = re.search(PATTERN, line)
    if match:
        for i in range(MAJ, RCV):
            result.append(match.group(i))
        rcv = match.group('rcv')
        if rcv:
            result.append(rcv)
    return result


def build_version(version_numbers):
    """
    Builds the version string
    :param version_numbers: the list with the version numbers
    :return: the version string
    """
    if len(version_numbers) > 3:
        result = CAND_VER
    else:
        result = BASIC_VER
    return result.format(*version_numbers)


def replace_version(replacement, line):
    """
    Replaces current version with input version if the line matches the pattern
    :param replacement: the version string
    :param line: the line in which the replacement is made
    :return:
    """
    line = re.sub(PATTERN, replacement, line)
    return line


def get_current_file_version():
    """
    Opens the version.py file and extracts the current version as a string
    :return: the current version string
    """
    global VERS_FILE
    with open(VERS_FILE, 'r') as ver_file:
        lines = ver_file.readlines()  # We read the whole file
        for line in lines:
            if 'VERSION =' in line:
                return build_version(get_version_numbers(line))
    raise EOFError()


def set_file_version(version):
    """
    Updates the text file version line with the received version
    :param version: the new version string line to set
    """
    global VERS_FILE
    try:
        # The 'U' flag forces universal break lines (Unix-like)
        with open(VERS_FILE, 'r+') as ver_file:
            lines = ver_file.readlines()  # We read the whole file
            # We get at the beginning
            ver_file.seek(0)
            # We delete everything from the beginning
            ver_file.truncate()

            for line in lines:
                if 'VERSION =' in line:
                    old_version = get_version_numbers(line)
                    line = replace_version(version, line)
                ver_file.write(line)
        return old_version
    except IOError:
        print('Error processing file')


def main():
    env = input_new_version = ''
    input_rel_cand_version = ''
    previous_version = get_current_file_version()
    print(f'Current version is: {previous_version}')

    while env not in ('dev', 'staging', 'production'):
        env = input('Deploy environment (production, staging and dev for origin): ')

    if env == 'dev':
        # No version, just upload all branches and exits
        os.popen(f'git push origin --all')
        print('Deployment finished')
        sys.exit(0)

    while not re.match(PATTERN, input_new_version):
        current_version = re.search(r'\d+\.\d+\.\d+', previous_version)
        if current_version:
            current_version = current_version.group()
        input_new_version = input(f'New version (Enter for current version {current_version}): ')
        if input_new_version.strip() == '':
            input_new_version = current_version
            if env == 'production':
                input_new_version = re.sub(r'-rc\d+', r'', input_new_version)
            break

    if env != 'production':
        while True:
            input_rel_cand_version = input(RC_INPUT_MSG).strip()
            if re.match(r'\d*', input_rel_cand_version):
                break

    # Completes 'new_version_numbers' and then builds 'new_version' string for writing the file
    new_version_numbers = get_version_numbers(input_new_version)
    prev_version_numbers = get_version_numbers(previous_version)

    if env != 'production':
        if input_rel_cand_version == '0':
            pass
        elif re.match(r'\d+', input_rel_cand_version):
            new_version_numbers.append(input_rel_cand_version)
        elif input_rel_cand_version == '':
            input_rel_cand_version = '1'
            if len(prev_version_numbers) == 4:
                if prev_version_numbers[:3] == new_version_numbers:
                    input_rel_cand_version = str(int(prev_version_numbers[-1]) + 1)

            if len(new_version_numbers) == 3:
                new_version_numbers.append(input_rel_cand_version)
            elif len(new_version_numbers) == 4:
                # Doesn't append but substitutes
                new_version_numbers[-1] = input_rel_cand_version

    new_version = build_version(new_version_numbers)

    if env != 'dev':
        # Check if version already exists, abort if positive
        tags = os.popen('git tag').read()
        if new_version in tags.split('\n'):
            print('This version already exists')
            sys.exit(0)

    print(f'{previous_version} ==> {new_version}')

    current_branch = os.popen('git symbolic-ref --short -q HEAD').read().strip()

    if 'y' not in input(f'\nConfirm pushing branch {current_branch.upper()} to {TARGET_BRANCH_NAME} for {env.upper()}? [y/n]: '):
        print('Aborted')
        sys.exit(0)

    set_file_version(new_version)
    os.system(f'git commit {version_file_path} -m "({new_version})" ')
    print('Commited version')
    if env == 'staging':
        command = os.popen(f'git push -f {env} {current_branch}:{TARGET_BRANCH_NAME}')
        command.close()
        print('Deployment finished.')
    elif env == 'production':
        command = os.popen(f'git push {env} {current_branch}:{TARGET_BRANCH_NAME}')
        error = command.close()
        if not error:
            os.popen(f'git tag {new_version}')
        print('Deployment finished.')


if __name__ == '__main__':
    main()


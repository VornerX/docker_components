import os
import shutil
from git import Repo
from helpers.color_print import ColorPrint
from config import GIT_REPOSITORIES, HOME_DEPLOYMENT_DIR

cprint = ColorPrint()


def clone_repositories():
    if os.path.exists(HOME_DEPLOYMENT_DIR):
        shutil.rmtree(HOME_DEPLOYMENT_DIR)

    for component_name, repo_settings in GIT_REPOSITORIES.items():

        os.makedirs(repo_settings['local_dir'], exist_ok=True)

        # TODO: if dir with repo already exists - do something
        Repo.clone_from(
            url=repo_settings['url'],
            to_path=repo_settings['local_dir'],
            branch=repo_settings['branch']
        )

        cprint.purple(str.format(
            '{} successfully cloned from branch {}.',
            repo_settings['url'],
            repo_settings['branch']
        ))

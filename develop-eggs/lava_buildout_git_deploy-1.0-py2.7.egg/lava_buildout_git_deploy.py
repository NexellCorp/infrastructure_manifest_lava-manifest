import os
import subprocess
import urllib

import zc.buildout
import zc.buildout.easy_install

def enable_git_repo_deployment(buildout):

    versions = buildout['buildout'].get('versions')
    if versions:
        versions = buildout[versions]
    else:
        versions = {}

    git_cache_dir = buildout._buildout_path('git-cache')

    git_source_repo_dir = os.path.join(git_cache_dir, 'source')
    if not os.path.exists(git_source_repo_dir):
        os.makedirs(git_source_repo_dir)

    git_export_path = os.path.join(git_cache_dir, 'exports')
    if not os.path.exists(git_export_path):
        os.makedirs(git_export_path)

    for egg_name, repository in buildout['git-repos'].items():
        head = buildout.get('git-heads', {}).get(egg_name)
        if head is None:
            head = 'master'

        if egg_name in versions:
            raise zc.buildout.UserError(
                '%s is sourced from a git repository and cannot also have a '
                'required version' % (egg_name,))

        buildout._logger.info('using %s from %s at %s', egg_name, repository,
                              head)

        # clone or update the source repository
        repository_cache = os.path.join(git_source_repo_dir,
                                        urllib.quote(repository, ''))

        # Remove previously existing bare repositories - they don't work
        if os.path.exists(repository_cache) and \
           os.path.exists(os.path.join(repository_cache, 'config')) and \
           os.path.exists(os.path.join(repository_cache, 'refs')) and \
           os.path.exists(os.path.join(repository_cache, 'branches')):
            subprocess.check_call(['rm', '-rf', repository_cache])

        if os.path.exists(repository_cache):
            git_fetch = subprocess.Popen(['git', 'pull'],
                                         cwd=repository_cache)
            git_fetch.wait()
        else:
            git_clone = subprocess.Popen(['git', 'clone', repository,
                                          repository_cache])
            git_clone.wait()

        # export requested head
        export_target = os.path.join(git_export_path, egg_name,
                                     describe(repository_cache, head))

        commit = resolve_commit(repository_cache, head)

        # we assume an export that was already done is good
        if not os.path.exists(export_target):
            os.makedirs(export_target)
            git_archive = subprocess.Popen(['git', 'archive', commit],
                                           stdout=subprocess.PIPE,
                                           cwd=repository_cache)
            tar_extract = subprocess.Popen(['tar', 'x'],
                                           stdin=git_archive.stdout,
                                           cwd=export_target)
            git_archive.wait()
            tar_extract.wait()

        # install the exported copy
        zc.buildout.easy_install.develop(
            export_target,
            buildout['buildout']['develop-eggs-directory'])

devnull = open(os.devnull, 'w')

def describe(repository, head):
    description = None
    commit = resolve_commit(repository, head)
    try:
        description = subprocess.check_output(
            ['git', 'describe', '--tags', commit],
            cwd=repository, stderr=devnull
        ).strip()
    except subprocess.CalledProcessError:
        description = subprocess.check_output(
            ['git', 'log', '--max-count=1', '--pretty=%ad-%h', '--date=short',
             commit],
            cwd=repository
        ).strip()
    return description

def resolve_commit(repository, head):
    commit = None
    try:
        commit = subprocess.check_output(['git', 'log', '--max-count=1',
                                          '--pretty=%H', head],
                                         cwd=repository, stderr=devnull).strip()
    except subprocess.CalledProcessError:
        if head.startswith('origin/'):
            raise RuntimeError("Could not resolve head %r" % head)
        else:
            commit = resolve_commit(repository, 'origin/'+ head)
    return commit


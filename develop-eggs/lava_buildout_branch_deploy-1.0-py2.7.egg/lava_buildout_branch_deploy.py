import os
import urllib

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import BzrBranch
from bzrlib.errors import BzrError
from bzrlib.plugin import load_plugins
from bzrlib.revisionspec import RevisionSpec
from bzrlib.transport import get_transport
import zc.buildout
import zc.buildout.easy_install


def revision_info(branch, rev_str):
    branch.lock_read()
    try:
        rev_spec = RevisionSpec.from_string(rev_str)
        revision_id = rev_spec.as_revision_id(branch)
        dotted_revno = branch.revision_id_to_dotted_revno(revision_id)
        revno = '.'.join(str(i) for i in dotted_revno)
        return revno, revision_id
    finally:
        branch.unlock()


# A word or two on the branch cache.
#
# We cache the branch referred to in the [branches] section in
# "source-branches" and then make a snapshot of it (so that even if an
# instance is tracking tip of a branch, it doesn't get a new version until
# _that_ instance is upgraded) in "checkouts"
#
# To keep updates quick, we only update the remote branch when:
#
#  1. The requested revision is not in the cached branch.
#  2. buildout['newest'] is in effect, i.e. -n was passed to buildout.
#
# So we should all probably get in the habit of running rebuildout -n every so
# often.
#
# branch-cache/
#   $egg-name/  # This is a shared repo
#     source-branches/ # The branch referred to in the [branches] section is
#                      # cloned into here (without a working tree though)
#       lp%3A$egg-name # we URL-encode the url of the branch to get a directory name
#     checkouts/ # The specific revision of the branch is cloned into here.
#       544-michael.hudson@lina.... # The directory is named $revno-$revid
#                                   # This is the directory that is fed to
#                                   # zc.buildout.easy_install.develop

def enable_branch_deployment(buildout):

    load_plugins()

    branch_cache_dir = buildout._buildout_path('branch-cache')

    if not os.path.exists(branch_cache_dir):
        buildout._logger.info("Creating branch cache directory")
        os.mkdir(branch_cache_dir)

    # Do a couple of quick checks.
    allow_picked_versions = buildout['buildout'].get_bool('allow-picked-versions')
    versions = buildout['buildout'].get('versions')
    if versions:
        versions = buildout[versions]
    else:
        versions = {}

    for egg_name, branch_loc in buildout['branches'].items():
        rev = buildout.get('revisions', {}).get(egg_name)
        if rev is None and not allow_picked_versions:
            raise zc.buildout.UserError(
                'No revision specified for %s' % (egg_name,)
                )
        if egg_name in versions:
            raise zc.buildout.UserError(
                '%s is sourced from a branch and cannot also have a required '
                'version' % (egg_name,)
                )

    # XXX There are some potential races if more than one instance is running
    # at once.
    for egg_name, branch_loc in buildout['branches'].items():
        rev = buildout.get('revisions', {}).get(egg_name)
        if rev is not None:
            buildout._logger.info('using %s at revision %s of %s', egg_name, rev, branch_loc)
        else:
            buildout._logger.info('using %s at tip of %s', egg_name, branch_loc)

        repo = os.path.join(branch_cache_dir, egg_name)
        if not os.path.exists(repo):
            branch_bzrdir = BzrDir.create(repo)
            branch_bzrdir.create_repository(shared=True)
            os.mkdir(os.path.join(repo, 'source-branches'))
            os.mkdir(os.path.join(repo, 'checkouts'))

        source_branch_dir = os.path.join(repo, 'source-branches', urllib.quote(branch_loc, ''))
        remote_branch = None
        if not os.path.exists(source_branch_dir):
            remote_branch = BzrBranch.open(branch_loc)
            bzr_branch = remote_branch.create_clone_on_transport(
                get_transport(source_branch_dir), no_tree=True)
            created = True
        else:
            created = False
            bzr_branch = BzrBranch.open(source_branch_dir)

        if rev is not None:
            try:
                revno, revid = revision_info(bzr_branch, rev)
            except BzrError:
                # If the specified revision was not in the branch, try pulling
                # again.
                if remote_branch is None:
                    remote_branch = BzrBranch.open(branch_loc)
                bzr_branch.pull(remote_branch, overwrite=True)
                try:
                    revno, revid = revision_info(bzr_branch, rev)
                except BzrError, e:
                    raise zc.buildout.UserError(
                        'Finding revid for revision %s of %s failed:\n%s' % (
                            rev, branch_loc, e)
                        )
        else:
            if buildout['buildout'].get_bool('newest') and not created:
                remote_branch = BzrBranch.open(branch_loc)
                bzr_branch.pull(remote_branch, overwrite=True)
            revno, revid = revision_info(bzr_branch, '-1')

        checkout_dir = os.path.join(repo, 'checkouts', '%s-%s'%(revno, revid))
        if not os.path.exists(checkout_dir):
            rev_branch = bzr_branch.create_clone_on_transport(
                get_transport(checkout_dir), revision_id=revid, no_tree=False)
            if not rev_branch.bzrdir.has_workingtree():
                rev_branch.bzrdir.create_workingtree()

        zc.buildout.easy_install.develop(
            buildout._buildout_path(checkout_dir),
            buildout['buildout']['develop-eggs-directory'])

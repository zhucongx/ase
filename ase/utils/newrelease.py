#!/usr/bin/env python3

"""Generate new release of ASE.

This script does not attempt to import ASE - then it would depend on
which ASE is installed and how - but assumes that it is run from the
ASE root directory."""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from time import strftime

os.environ['LANGUAGE'] = 'C'


def runcmd(cmd, output=False, error_ok=False):
    print('Executing:', cmd)
    try:
        if output:
            txt = subprocess.check_output(cmd, shell=True)
            return txt.decode('utf8')
        else:
            return subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as err:
        if error_ok:
            print('Failed: {}'.format(err))
            print('Continuing...')
        else:
            raise


bash = runcmd


def py(cmd, output=False):
    return runcmd('python3 {}'.format(cmd))


def git(cmd, error_ok=False):
    cmd = 'git {}'.format(cmd)
    return runcmd(cmd, output=True, error_ok=error_ok)


cwd = os.getcwd()
versionfile = 'ase/__init__.py'


def get_version():
    with open(versionfile) as fd:
        return re.search(r"__version__ = '(\S+)'", fd.read()).group(1)


def main():
    p = argparse.ArgumentParser(description='Generate new release of ASE.',
                                epilog='Run from the root directory of ASE.')
    p.add_argument('version', nargs=1,
                   help='version number for new release')
    # p.add_argument('nextversion', nargs=1,
    #                help='development version after release')
    p.add_argument('--clean', action='store_true',
                   help='delete release branch and tag')
    args = p.parse_args()

    try:
        current_version = get_version()
    except Exception as err:
        p.error('Cannot get version: {}.  Are you in the root directory?'
                .format(err))

    print('Current version: {}'.format(current_version))

    version = args.version[0]

    branchname = 'ase-{}'.format(version)
    current_version = get_version()

    if args.clean:
        print('Cleaning {}'.format(version))
        git('checkout master')
        # git('tag -d {}'.format(version), error_ok=True)
        git('branch -D {}'.format(branchname), error_ok=True)
        git('branch -D {}'.format('web-page'), error_ok=True)
        return

    print('New release: {}'.format(version))

    txt = git('status')
    branch = re.match(r'On branch (\S+)', txt).group(1)
    print('Creating new release from branch {}'.format(repr(branch)))
    git('checkout -b {}'.format(branchname))

    def update_version(version):
        print('Editing {}: version {}'.format(versionfile, version))
        new_versionline = "__version__ = '{}'\n".format(version)
        lines = []
        ok = False
        with open(versionfile) as fd:
            for line in fd:
                if line.startswith('__version__'):
                    ok = True
                    line = new_versionline
                lines.append(line)
        assert ok
        with open(versionfile, 'w') as fd:
            for line in lines:
                fd.write(line)

    update_version(version)

    releasenotes = 'doc/releasenotes.rst'

    searchtxt = re.escape("""\
Git master branch
=================

:git:`master <>`.
""")

    replacetxt = """\
Git master branch
=================

:git:`master <>`.

* No changes yet


{header}
{underline}

{date}: :git:`{version} <../{version}>`
"""

    date = strftime('%d %B %Y').lstrip('0')
    header = 'Version {}'.format(version)
    underline = '=' * len(header)
    replacetxt = replacetxt.format(header=header, version=version,
                                   underline=underline, date=date)

    print('Editing {}'.format(releasenotes))
    with open(releasenotes) as fd:
        txt = fd.read()
    txt, n = re.subn(searchtxt, replacetxt, txt, re.MULTILINE)
    assert n == 1

    with open(releasenotes, 'w') as fd:
        fd.write(txt)

    searchtxt = """\
News
====
"""

    replacetxt = """\
News
====

* :ref:`ASE version {version} <releasenotes>` released ({date}).
"""

    replacetxt = replacetxt.format(version=version, date=date)

    frontpage = 'doc/index.rst'

    print('Editing {}'.format(frontpage))
    with open(frontpage) as fd:
        txt = fd.read()
    txt, n = re.subn(searchtxt, replacetxt, txt)
    assert n == 1
    with open(frontpage, 'w') as fd:
        fd.write(txt)

    installdoc = 'doc/install.rst'
    print('Editing {}'.format(installdoc))

    with open(installdoc) as fd:
        txt = fd.read()

    txt, nsub = re.subn(r'ase-\d+\.\d+\.\d+',
                        'ase-{}'.format(version), txt)
    assert nsub > 0
    txt, nsub = re.subn(r'git clone -b \d+\.\d+\.\d+',
                        'git clone -b {}'.format(version), txt)
    assert nsub == 1

    with open(installdoc, 'w') as fd:
        fd.write(txt)

    git('add {}'.format(' '.join([versionfile, installdoc,
                                  frontpage, releasenotes])))
    git('commit -m "ASE version {}"'.format(version))
    # git('tag -s {0} -m "ase-{0}"'.format(version))

    buildpath = Path('build')
    if buildpath.is_dir():
        print('Removing stale build directory, since it exists')
        assert Path('ase/__init__.py').exists()
        assert Path('setup.py').exists()
        shutil.rmtree('build')
    else:
        print('No stale build directory found; proceeding')
    py('setup.py sdist > setup_sdist.log')
    py('setup.py bdist_wheel > setup_bdist_wheel3.log')
    bash('gpg --armor --yes --detach-sign dist/ase-{}.tar.gz'.format(version))

    print()
    print('Automatic steps done.')
    print()
    print('Now is a good time to:')
    print(' * check the diff')
    print(' * run the tests')
    print(' * verify the web-page build')
    print()
    print('Remaining steps')
    print('===============')
    print('git show {}  # Inspect!'.format(version))
    print('git checkout master')
    print('git merge {}'.format(branchname))
    print('twine upload '
          'dist/ase-{v}.tar.gz '
          'dist/ase-{v}-py3-none-any.whl '
          'dist/ase-{v}.tar.gz.asc'.format(v=version))
    print('git push --tags origin master  # Assuming your remote is "origin"')


if __name__ == '__main__':
    main()

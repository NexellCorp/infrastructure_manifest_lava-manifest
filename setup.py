# Copyright (C) 2012 Linaro Limited
#
# Author: Michael Hudson-Doyle
#
# This file is part of LAVA Server.
#
# LAVA Server is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation
#
# LAVA Server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with LAVA Server.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages


setup(
    name='lava-manifest',
    version="1.0",
    author="LAVA engineers",
    author_email="linaro-validation@lists.linaro.org",
    namespace_packages=['lava', 'lava.recipes'],
    packages=find_packages(),
    entry_points="""
        [zc.buildout]
        scripts = lava.recipes.scripts:Scripts
        wsgi = lava.recipes.wsgi:WSGIRecipe
        instance_path = lava.recipes.instance_path:InstancePath
        serversymlink = lava.recipes.server:ServerSymlink
        manifest = lava.recipes.manifest:ManifestRecipe
        [zc.buildout.uninstall]
        serversymlink = lava.recipes.server:uninstall_server_symlink
        """,
    license="AGPL",
    description="XXX",
    long_description="""
    XXX
    """,
    url='https://launchpad.net/lava-manifest',
    install_requires=[
        'zc.recipe.egg',
        'distribute',
    ],
    zip_safe=False)

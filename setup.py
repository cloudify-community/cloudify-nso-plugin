import os
import re
import sys
import pathlib
from setuptools import setup, find_packages


def get_version():
    current_dir = pathlib.Path(__file__).parent.resolve()
    with open(os.path.join(current_dir, 'fabric_plugin/__version__.py'),
              'r') as outfile:
        var = outfile.read()
        return re.search(r'\d+.\d+.\d+', var).group()


install_requires = [
    'requests'
]

if sys.version_info.major == 3 and sys.version_info.minor == 6:
    packages = ['nso_plugin']
    install_requires += [
        'cloudify-common>=4.5.5',
    ]
else:
    packages = find_packages()
    install_requires += [
        'fusion-common',
    ]


setup(
    zip_safe=True,
    name='cloudify-nso-plugin',
    version='1.0.0.0',
    author='Data Vision',
    author_email='info@datavision.com',
    packages=packages,
    license='LICENSE',
    description='Cloudify plugin for Cisco NSO',
    install_requires=install_requires
)

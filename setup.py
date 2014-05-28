# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='rof-rcon-client',
    version='0.1.0',
    url='https://github.com/vaal-/rof-rcon-client',
    license='BSD',
    author='Vladimir Ulupov',
    author_email='vladimir.ulupov@gmail.com',
    description='RCon client for Rise of Flight dedicated server.',
    # long_description=__doc__,
    py_modules=['rof_rcon_client'],
    install_requires=[
        'six==1.6.1',
    ],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Games/Entertainment',
        'Topic :: Software Development :: Libraries',
    ],
    keywords='rise of flight, rof, rcon, dserver'
)

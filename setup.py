from setuptools import setup, find_packages

setup(
    name='f2py-skel',
    version='0.0.1',
    packages=find_packages(include=['f2py']),
    install_requires=[
        'numpy>=1.20.x'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': ['f2py-skel=f2py.frontend.f2py2e:main']
    },
    extras_require={
        'interactive': ['ipython'],
    }
)

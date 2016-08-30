from setuptools import setup, find_packages

setup(
    name='applemonweb',
    version='0.1',
    description='Django project for Applemon',
    url='https://applemon.com/',
    author='Dara Adib',
    classifiers=[
       'Development Status :: 3 - Alpha',
       'Programming Language :: Python :: 3',
    ],
    packages=[],
    install_requires=[
        'django',
        'django-formtools',
        'django-mass-edit',
        'django-sql-explorer',
        'gunicorn',
    ],
    data_files=[],
)

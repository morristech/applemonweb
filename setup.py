from setuptools import setup


with open('requirements.in') as f:
    # requires = f.read().splitlines()
    requires = []
    for line in f:
        if line.startswith('-e'):
            requires.append(line.split('#egg=')[1])
        else:
            requires.append(line)

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
    install_requires=requires,
    data_files=[],
)

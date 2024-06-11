from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required_packages = f.read().splitlines()

setup(
    name='json3pdf',
    version='0.2.0',
    packages=find_packages(),
    install_requires=required_packages,
    entry_points={
        'console_scripts': [
            'json3pdf=json3pdf.main:main',
        ],
    },
)
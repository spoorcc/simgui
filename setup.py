from setuptools import setup, find_packages

setup(
    name='CustomLCD',
    version='0.1.0',
    description='A custom LCD package',
    author='Ben Spoor',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=['svg.path>=4.0.0'],
)
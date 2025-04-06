from setuptools import setup, find_packages

setup(
    name='dbviz',
    version='0.1',
    py_modules=['dbviz'],  # Ensure this matches the name of your Python file without the .py extension
    packages=find_packages(),
    install_requires=[
        'sqlparse',
        'setuptools'
    ],
    entry_points={
        'console_scripts': [
            'dbviz=dbviz:main',
        ],
    },
)
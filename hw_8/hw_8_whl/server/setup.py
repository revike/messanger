from setuptools import setup, find_packages

setup(name="messserverrevikeee",
      version="0.0.1",
      description="messserverrevikeee",
      author="Evgenii Fedorin",
      author_email="revike@ya.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex']
      )

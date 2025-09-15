from setuptools import setup, find_packages

setup(
    name="wall-e-mail",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-auth-oauthlib",
        "google-auth",
        "google-api-python-client",
        "pytest",
    ],
)
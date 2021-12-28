from setuptools import setup, find_packages  # type: ignore

setup(
    name='tagls',
    # The version will be updated automatically in CI
    version='unknown',
    description='A language server based on tags',
    author='daquexian',
    author_email='daquexian566@gmail.com',
    url='https://github.com/daquexian/tagls',
    packages=find_packages(),
    package_data={'': ['LICENSE']},
    license='Apache',
    install_requires=[
        'pygls-tagls-custom == 0.0.1'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development'
    ],
    python_requires='>=3.5'
)

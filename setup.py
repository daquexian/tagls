from setuptools import setup, find_packages  # type: ignore

setup(
    name='tagls',
    # The version will be updated automatically in CI
    version='0.0.0',
    description='A language server based on tags',
    author='daquexian',
    author_email='daquexian566@gmail.com',
    url='https://github.com/daquexian/tagls',
    packages=find_packages(),
    # package_data={'': ['LICENSE']},
    license='Apache',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development'
    ],
    python_requires='>=3.5'
)

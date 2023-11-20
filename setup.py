"""
Setuptools based setup module
"""
from setuptools import setup, find_packages
import versioneer


setup(
    name='pyiron_experimental',
    version=versioneer.get_version(),
    description='Repository for experimental plugins to the pyiron IDE.',
    long_description='http://pyiron.org',

    url='https://github.com/pyiron/pyiron_experimental',
    author='Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department',
    author_email='hassani@mpie.de',
    license='BSD',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],

    keywords='pyiron',
    packages=find_packages(exclude=["*tests*"]),
    install_requires=[
        'pyiron_base==0.6.6',
        'matplotlib==3.8.1',
        'pystem==0.0.26',
        'hyperspy==1.7.6',
        'scanf==1.5.2',
    ],
    cmdclass=versioneer.get_cmdclass(),
)

from setuptools import setup, find_packages

version = '0.1'

setup(name='ezjailremote.flavours.elektropost',
      version=version,
      description="ezjail-remote flavour that installs the elektropost"
        "stack (http://erdgeist.org/arts/software/elektropost/)",
      long_description=open("README.txt").read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='ezjail elektropost',
      author='Tom Lazar',
      author_email='tom@tomster.org',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['ezjailremote', 'ezjailremote.flavours'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'ezjailremote',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )

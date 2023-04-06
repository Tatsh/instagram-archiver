from setuptools import find_packages, setup

with open('README.md') as f:
    setup(author='Andrew Udvare',
          author_email='audvare@gmail.com',
          description='Archive Instagram content.',
          entry_points={'console_scripts': ['ia = instagram_archiver:main']},
          extras_require={
              'dev': [
                  'mypy', 'mypy-extensions', 'pylint', 'pylint-quotes', 'rope',
                  'types-requests>=2.25.9'
              ]
          },
          install_requires=[
              'click>=8.0.0', 'loguru>=0.5.3', 'requests', 'yt-dlp>=2022.7.18'
          ],
          license='MIT',
          long_description=f.read(),
          long_description_content_type='text/markdown',
          name='instagram-archiver',
          packages=find_packages(),
          python_requires='>=3.9',
          url='https://github.com/Tatsh/instagram-archiver',
          version='0.0.6')

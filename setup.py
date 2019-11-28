import setuptools

with open("README.md", "rt") as fh:
    long_description = fh.read()

with open('requirements.txt', 'rt') as f:
    dependencies = f.read().split('\n')

setuptools.setup(
     name='asb',
     version='0.2',
     author="Luis Rojas Aguilera",
     author_email="rojas@icomp.ufam.edu.br",
     description="Python utility to capture android screen frames in real time and use with 3rd party libs like opencv.",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/roj4s/android_screen_buffer",
     packages=setuptools.find_packages(),
     include_package_data=True,
     install_requires=dependencies,
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],
 )



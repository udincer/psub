import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="psub", 
    version="0.1.0_alpha",
    author="Tev Dincer",
    author_email="umutdincer@gmail.com",
    description="Submit array jobs to a SGE cluster without all the suffering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/udincer/psub",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    entry_points={'console_scripts': ['psub = psub.cli:main']}
)

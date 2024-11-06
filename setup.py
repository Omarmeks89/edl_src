from setuptools import setup, find_packages


if __name__ == "__main__":
    setup(
            name="edl_translator",
            version="0.1.8",
            package_dir={"": "src"},
            packages=find_packages("src", include=["src"])
    )
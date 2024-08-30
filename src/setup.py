from setuptools import setup, find_packages

setup(
    name="ai-researcher",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "langchain_community",
        "langchain_openai",
        "langgraph",
        "wikipedia",
        "scikit-learn",
        "langchain_fireworks",
        "duckduckgo-search",
        "tavily-python",
        "pydantic",
    ],
    author="Pranav Dhoolia, Avijit Prasad",
    author_email="pranav@dhoolia.com, avijits01@gmail.com",
    description="A module for conducting deep research on topics using AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/esxr/ai-researcher",
)

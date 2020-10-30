# Contributing

🎉 Thank you for taking the time to contribute to ``pyinfra``! 🎉

Third party pull requests help expand pyinfra's functionality and are essential to it's continued growth. This guide should help get you started adding additional operations/facts to pyinfra.

## Guides

+ [How to write operations](api/operations)
+ [How to write facts](api/facts)
+ [How to write connectors](api/connectors)
+ [API reference](api/reference)

## Dev Setup

```sh
# Create a virtualenv with your tool of choice
# python -m venv / pyenv virtualenv / virtualenv

# Clone the repo
git clone git@github.com:Fizzadar/pyinfra.git

# Install the package in editable mode with development requirements
cd pyinfra
pip install -e '.[dev]'
```

## Tests

Use `pytest` to run tests, or `pytest --cov` to run with coverage. Pull requests are expected to be tested and not drop overall project coverage by >1%.

## Generate Documentation

To generate:

```sh
sphinx-build -a docs/ docs/build/
```

To view ([localhost:8000](http://localhost:8000)):

```sh
python -m http.server -d docs/build/
```

## Code Style

+ 100 max line length
+ no hanging indents
+ single quotes everywhere possible

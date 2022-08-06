install_dev:
	pip install -e '.[extra]'

install_docs:
	pip install -e '.[docs]'

test:
	pytest --cov

.PHONY: docs
docs:
	sphinx-build -a docs/ docs/build/

docs_serve:
	python3 -m http.server -d docs/build/


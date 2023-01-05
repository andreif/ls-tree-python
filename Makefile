
x:
	venv/bin/poetry run ls-tree venv

t: clean install

.git/hooks:
	venv/bin/pre-commit install

clean:
	rm -rf .git/hooks
	rm -rf .venv
	rm -rf venv
	rm -rf dist

lock:
	venv/bin/poetry check
	venv/bin/poetry lock

sync:
	venv/bin/poetry lock --check
	venv/bin/poetry install --sync --no-ansi

install: setup .venv
.venv:
	@deactivate || true 2>/dev/null
	venv/bin/poetry install --sync --no-ansi
	venv/bin/poetry show --tree

setup: venv .git/hooks
venv:
	@deactivate || true 2>/dev/null
	python --version
	python -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install wheel poetry tox pre-commit
	venv/bin/pip list

pyenv:
	pyenv install --skip-existing 3.9:latest
	pyenv install --skip-existing 3.10:latest
	pyenv install --skip-existing 3.11:latest
	pyenv local $(shell pyenv latest 3.9) $(shell pyenv latest 3.10) $(shell pyenv latest 3.11)

lint:
	pre-commit run --all-files

publish:
	venv/bin/poetry publish --build ${PYPI_AUTH}  # --dry-run

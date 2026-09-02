.PHONY: test test-fast test-python test-java test-web help

help:
	@echo "make test-fast   - run all fast unit tests (default)"
	@echo "make test        - alias for test-fast"
	@echo "make test-python - pytest in main/xiaozhi-server"
	@echo "make test-java   - mvn test in main/manager-api"
	@echo "make test-web    - npm run test:unit in main/manager-web"

test: test-fast

test-fast: test-python test-java test-web

test-python:
	cd main/xiaozhi-server && python -m pytest -x -q

test-java:
	cd main/manager-api && mvn -B -q test -DfailIfNoTests=false

test-web:
	cd main/manager-web && npm ci --no-audit --no-fund && npm test

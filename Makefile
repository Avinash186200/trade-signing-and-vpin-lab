.PHONY: install test bench bench-dev report demo

install:
	pip install -c constraints.txt -e ".[dev]"

test:
	pytest -q

# Offline, deterministic: simulate 32 sessions, choose VPIN settings on development seeds,
# score held-out seeds once. Writes results/*.json and RESULTS.md.
bench:
	python -m tsvlab.cli bench --out results

# Development seeds only (selection and thresholds); never touches the held-out seeds.
bench-dev:
	python -m tsvlab.cli bench --dev-only --out out/dev

report:
	python -m tsvlab.cli report --out results

# One informed session as CSV: trades with true sides and each rule's signs, and quotes.
demo:
	python -m tsvlab.cli simulate --mode informed --seed 1 --out data

PY ?= python3
WS ?= /tmp/demo

.PHONY: test matrix demo install lens export clean

test:            ## behaviour suite
	$(PY) tests/test_gate.py

matrix:          ## 500-case matrix
	$(PY) tests/test_matrix.py

demo:            ## the two-task scene against $(WS)
	sh demo.sh $(WS)

demo-commands:   ## the command-contradiction scene
	sh demo2.sh $(WS)

install:         ## machine-wide instal
	sh install.sh --global

lens:            ## render the evidence page for $(WS)
	$(PY) lens.py $(WS) -o $(WS)/lens.html

export:          ## hashed evidence record per task
	COUNTERSIGN_WORKSPACE=$(WS) $(PY) countersign.py export

clean:
	rm -rf .countersign

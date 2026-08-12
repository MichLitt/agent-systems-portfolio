.PHONY: docs readiness require-release require-demo require-evidence refresh test finetune-smoke closure check check-ablation-protocol build-g3-corpus

docs:
	python3 scripts/check_workspace_docs.py

readiness:
	python3 scripts/check_delivery_readiness.py

require-release:
	python3 scripts/check_delivery_readiness.py --require release

require-demo:
	python3 scripts/check_delivery_readiness.py --require demo

require-evidence:
	python3 scripts/check_delivery_readiness.py --require evidence

check-ablation-protocol:
	python3 scripts/validate_g3_ablation_protocol.py

build-g3-corpus:
	./scripts/build_g3_rag_corpus.sh

refresh:
	./scripts/refresh_workspace_after_move.sh

test:
	./scripts/check_core_projects.sh

finetune-smoke:
	./scripts/check_finetune_project.sh

closure:
	./scripts/run_three_project_closure.sh

check: docs readiness test finetune-smoke closure

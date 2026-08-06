.PHONY: docs refresh test finetune-smoke closure check

docs:
	python3 scripts/check_workspace_docs.py

refresh:
	./scripts/refresh_workspace_after_move.sh

test:
	./scripts/check_core_projects.sh

finetune-smoke:
	./scripts/check_finetune_project.sh

closure:
	./scripts/run_three_project_closure.sh

check: docs test finetune-smoke closure

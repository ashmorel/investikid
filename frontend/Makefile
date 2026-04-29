.PHONY: smoke
smoke:
	@cd ../backend && (lsof -i :8000 | grep -q uvicorn || (source .venv/bin/activate && nohup uvicorn app.main:app --port 8000 --log-level warning > /tmp/4b-uvicorn.log 2>&1 &))
	@sleep 3
	npm run test:e2e

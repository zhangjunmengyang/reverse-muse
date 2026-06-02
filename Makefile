.PHONY: help start stop restart logs status clean force-clean healthcheck \
	logs-backend logs-frontend version db-start db-stop

# ============================================
# 配置
# ============================================
PROJECT_ROOT := $(shell pwd)
PID_DIR := .pids
LOG_DIR := .logs

# 端口配置
BACKEND_PORT := 8001
FRONTEND_PORT := 3001
DB_PORT := 8000

# Runtime commands. Prefer the repo-local virtualenv, then fall back to PATH.
PYTHON ?= $(shell if [ -x "$(PROJECT_ROOT)/.venv/bin/python" ]; then echo "$(PROJECT_ROOT)/.venv/bin/python"; else command -v python3 || command -v python; fi)
NPM ?= $(shell command -v npm || echo npm)

# 超时配置
KILL_TIMEOUT := 3
HEALTH_TIMEOUT := 30

# Docker Compose
DOCKER := $(shell command -v docker 2>/dev/null)
DOCKER_COMPOSE := $(shell if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; fi)

# ============================================
# 帮助
# ============================================
help:
	@echo ""
	@echo "  Reverse Muse - 开发环境管理"
	@echo "  ============================"
	@echo ""
	@echo "  命令:"
	@echo "    make start       - 启动所有服务 (DB + Backend + Frontend)"
	@echo "    make stop        - 停止所有服务"
	@echo "    make restart     - 重启所有服务"
	@echo ""
	@echo "    make db-start    - 仅启动数据库 (SurrealDB)"
	@echo "    make db-stop     - 仅停止数据库"
	@echo ""
	@echo "    make status      - 查看服务状态"
	@echo "    make healthcheck - 健康检查"
	@echo "    make logs        - 查看所有日志"
	@echo "    make logs-backend  - 实时查看后端日志"
	@echo "    make logs-frontend - 实时查看前端日志"
	@echo ""
	@echo "    make clean       - 清理环境"
	@echo "    make force-clean - 强制清理 (端口被占用时使用)"
	@echo "    make version     - 显示版本信息"
	@echo ""
	@echo "  服务地址:"
	@echo "    前端:     http://localhost:$(FRONTEND_PORT)"
	@echo "    后端 API: http://localhost:$(BACKEND_PORT)"
	@echo "    API 文档: http://localhost:$(BACKEND_PORT)/docs"
	@echo "    数据库:   http://localhost:$(DB_PORT)"
	@echo ""

# ============================================
# 启动服务
# ============================================
start: _ensure_dirs db-start _start_backend _start_frontend
	@echo ""
	@echo "=========================================="
	@echo "  所有服务已启动"
	@echo "=========================================="
	@echo ""
	@$(MAKE) healthcheck
	@echo ""
	@echo "  前端:     http://localhost:$(FRONTEND_PORT)"
	@echo "  后端 API: http://localhost:$(BACKEND_PORT)"
	@echo "  API 文档: http://localhost:$(BACKEND_PORT)/docs"
	@echo ""

_ensure_dirs:
	@mkdir -p $(PID_DIR) $(LOG_DIR)

db-start:
	@echo "[1/3] 启动数据库 (SurrealDB)..."
	@if [ -z "$(DOCKER)" ] || [ -z "$(DOCKER_COMPOSE)" ]; then \
		echo "  跳过数据库：未找到 Docker / Docker Compose"; \
	elif docker ps --format '{{.Names}}' | grep -q "reverse-muse-db"; then \
		echo "  数据库已在运行"; \
	else \
		$(DOCKER_COMPOSE) -f docker-compose.yml up -d 2>&1 | grep -v "^$$" || true; \
		echo "  等待数据库就绪..."; \
		sleep 3; \
	fi

_start_backend:
	@echo "[2/3] 启动后端服务..."
	@if lsof -ti :$(BACKEND_PORT) >/dev/null 2>&1; then \
		echo "  后端已在运行 (端口 $(BACKEND_PORT))"; \
	else \
		PYTHONPATH=$(PROJECT_ROOT) nohup $(PYTHON) -m uvicorn apps.backend.app.main:app \
			--host 0.0.0.0 --port $(BACKEND_PORT) \
			> $(LOG_DIR)/backend.log 2>&1 & echo $$! > $(PID_DIR)/backend.pid; \
		for i in $$(seq 1 $(HEALTH_TIMEOUT)); do \
			if curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null 2>&1; then \
				echo "  后端启动成功"; \
				exit 0; \
			fi; \
			sleep 1; \
		done; \
		echo "  后端启动失败，查看日志: make logs-backend"; \
		exit 1; \
	fi

_start_frontend:
	@echo "[3/3] 启动前端服务..."
	@if lsof -ti :$(FRONTEND_PORT) >/dev/null 2>&1; then \
		echo "  前端已在运行 (端口 $(FRONTEND_PORT))"; \
	else \
		nohup sh -c 'cd apps/frontend && exec $(NPM) run dev -- --port $(FRONTEND_PORT)' \
			> $(PROJECT_ROOT)/$(LOG_DIR)/frontend.log 2>&1 & echo $$! > $(PROJECT_ROOT)/$(PID_DIR)/frontend.pid; \
		for i in $$(seq 1 $(HEALTH_TIMEOUT)); do \
			if curl -sf http://localhost:$(FRONTEND_PORT) >/dev/null 2>&1; then \
				echo "  前端启动成功"; \
				exit 0; \
			fi; \
			sleep 1; \
		done; \
		echo "  前端启动失败，查看日志: make logs-frontend"; \
		exit 1; \
	fi

# ============================================
# 停止服务
# ============================================
stop: _stop_frontend _stop_backend db-stop
	@echo ""
	@echo "所有服务已停止"

_stop_backend:
	@echo "[1/3] 停止后端服务..."
	@-pkill -f "uvicorn apps.backend.app.main:app" 2>/dev/null || true
	@-lsof -ti :$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	@rm -f $(PID_DIR)/backend.pid 2>/dev/null || true
	@echo "  后端已停止"

_stop_frontend:
	@echo "[2/3] 停止前端服务..."
	@-pkill -f "next dev" 2>/dev/null || true
	@-pkill -f "next-router-worker" 2>/dev/null || true
	@-lsof -ti :$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true
	@rm -f $(PID_DIR)/frontend.pid 2>/dev/null || true
	@echo "  前端已停止"

db-stop:
	@echo "[3/3] 停止数据库..."
	@if [ -n "$(DOCKER_COMPOSE)" ]; then \
		$(DOCKER_COMPOSE) -f docker-compose.yml down 2>/dev/null || true; \
	fi
	@echo "  数据库已停止"

# ============================================
# 重启服务
# ============================================
restart:
	@echo "重启所有服务..."
	@$(MAKE) stop
	@sleep 2
	@$(MAKE) start

# ============================================
# 状态查看
# ============================================
status:
	@echo ""
	@echo "=== 服务状态 ==="
	@echo ""
	@printf "  数据库 (SurrealDB) ... "
	@if [ -z "$(DOCKER)" ]; then \
		printf "\033[33m不可用\033[0m (未找到 Docker)\n"; \
	elif docker ps --format '{{.Names}}' | grep -q "reverse-muse-db"; then \
		printf "\033[32m运行中\033[0m (端口 $(DB_PORT))\n"; \
	else \
		printf "\033[31m未运行\033[0m\n"; \
	fi
	@printf "  后端 (FastAPI) ....... "
	@if lsof -ti :$(BACKEND_PORT) >/dev/null 2>&1; then \
		printf "\033[32m运行中\033[0m (端口 $(BACKEND_PORT))\n"; \
	else \
		printf "\033[31m未运行\033[0m\n"; \
	fi
	@printf "  前端 (Next.js) ....... "
	@if lsof -ti :$(FRONTEND_PORT) >/dev/null 2>&1; then \
		printf "\033[32m运行中\033[0m (端口 $(FRONTEND_PORT))\n"; \
	else \
		printf "\033[31m未运行\033[0m\n"; \
	fi
	@echo ""

# ============================================
# 健康检查
# ============================================
healthcheck:
	@echo ""
	@echo "=== 健康检查 ==="
	@echo ""
	@failed=0; \
	printf "  数据库 ............... "; \
	if [ -z "$(DOCKER)" ]; then \
		printf "\033[33mWARN\033[0m (未找到 Docker，跳过 SurrealDB)\n"; \
	elif docker ps --format '{{.Names}}' | grep -q "reverse-muse-db"; then \
		printf "\033[32mOK\033[0m\n"; \
	else \
		printf "\033[31mFAIL\033[0m\n"; \
		failed=1; \
	fi; \
	printf "  后端 API ............. "; \
	if curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null 2>&1; then \
		printf "\033[32mOK\033[0m\n"; \
	else \
		printf "\033[31mFAIL\033[0m\n"; \
		failed=1; \
	fi; \
	printf "  前端 ................. "; \
	if lsof -ti :$(FRONTEND_PORT) >/dev/null 2>&1; then \
		printf "\033[32mOK\033[0m\n"; \
	else \
		printf "\033[33mWARN\033[0m (可能正在编译)\n"; \
	fi; \
	echo ""; \
	if [ $$failed -eq 1 ]; then \
		echo "  部分服务异常，运行 'make logs' 查看日志"; \
		exit 1; \
	fi

# ============================================
# 日志查看
# ============================================
logs:
	@echo ""
	@echo "=== 后端日志 (最近 20 行) ==="
	@tail -20 $(LOG_DIR)/backend.log 2>/dev/null || echo "(无日志)"
	@echo ""
	@echo "=== 前端日志 (最近 10 行) ==="
	@tail -10 $(LOG_DIR)/frontend.log 2>/dev/null || echo "(无日志)"
	@echo ""
	@echo "实时日志: make logs-backend 或 make logs-frontend"

logs-backend:
	@echo "后端日志 (Ctrl+C 退出):"
	@tail -f $(LOG_DIR)/backend.log 2>/dev/null || echo "日志文件不存在"

logs-frontend:
	@echo "前端日志 (Ctrl+C 退出):"
	@tail -f $(LOG_DIR)/frontend.log 2>/dev/null || echo "日志文件不存在"

# ============================================
# 清理
# ============================================
clean:
	@echo "清理环境..."
	@$(MAKE) stop
	@rm -rf $(PID_DIR) $(LOG_DIR)
	@echo "清理完成"

force-clean:
	@echo "强制清理所有进程和端口..."
	@echo ""
	@echo "[1/3] 清理进程..."
	@-pkill -9 -f "uvicorn apps.backend" 2>/dev/null || true
	@-pkill -9 -f "next dev" 2>/dev/null || true
	@-pkill -9 -f "next-router-worker" 2>/dev/null || true
	@echo ""
	@echo "[2/3] 清理端口..."
	@for port in $(BACKEND_PORT) $(FRONTEND_PORT); do \
		pids=$$(lsof -ti :$$port 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "  清理端口 $$port: $$pids"; \
			echo "$$pids" | xargs kill -9 2>/dev/null || true; \
		fi; \
	done
	@echo ""
	@echo "[3/3] 清理 Docker..."
	@if [ -n "$(DOCKER_COMPOSE)" ]; then \
		$(DOCKER_COMPOSE) -f docker-compose.yml down --remove-orphans 2>/dev/null || true; \
	fi
	@echo ""
	@rm -rf $(PID_DIR) $(LOG_DIR)
	@echo "强制清理完成"

# ============================================
# 版本信息
# ============================================
version:
	@echo ""
	@echo "Reverse Muse"
	@echo "============"
	@echo "Docker:  $$(if command -v docker >/dev/null 2>&1; then docker --version | cut -d' ' -f3 | tr -d ','; else echo '未安装'; fi)"
	@echo "Python:  $$($(PYTHON) --version 2>/dev/null | cut -d' ' -f2 || echo '未安装')"
	@echo "Node:    $$(node --version 2>/dev/null || echo '未安装')"
	@echo "npm:     $$($(NPM) --version 2>/dev/null || echo '未安装')"
	@echo ""

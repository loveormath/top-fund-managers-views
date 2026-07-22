from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from .score_service import generate_fund_prompt_service

from .config import AppConfig
from .database import Database, utcnow
from .deepseek import DeepSeekGateway
from .registry import ManagerRegistry
from .retrieval import CorpusIndex
from .runs import EventHub, RunService
from .schemas import (
    ApiMessage,
    DeepSeekKeyInput,
    IndexStatus,
    RunCreate,
    RunPublic,
    SettingsPatch,
    SettingsPublic,
    ThreadCreate,
    ThreadPublic,
)
from .security import SecretBox
from .workflow import build_workflow


async def _rebuild(app: FastAPI) -> None:
    try:
        await asyncio.to_thread(app.state.index.rebuild)
    finally:
        app.state.index_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig.from_env()
    db = Database(config.database_path)
    registry = ManagerRegistry(config.registry_path, config.root_dir)
    corpus_index = CorpusIndex(config, registry)
    secrets = SecretBox(config.secret_key_path, config.app_encryption_key)
    gateway = DeepSeekGateway(config, db, secrets)
    events = EventHub(db)
    async with AsyncSqliteSaver.from_conn_string(str(config.checkpoint_path)) as checkpointer:
        graph = build_workflow(registry, corpus_index, gateway, events.emit, checkpointer)
        app.state.config = config
        app.state.db = db
        app.state.registry = registry
        app.state.index = corpus_index
        app.state.gateway = gateway
        app.state.events = events
        app.state.runs = RunService(db, graph, events)
        app.state.index_task = None
        if os.getenv("FUND_INSIGHT_AUTO_INDEX", "1") == "1" and corpus_index.status()["state"] == "empty":
            app.state.index_task = asyncio.create_task(_rebuild(app), name="initial-index-build")
        yield
        if app.state.index_task:
            app.state.index_task.cancel()
        await app.state.runs.shutdown()
    corpus_index.close()
    db.close()


app = FastAPI(
    title="Fund Insight API",
    version="1.0.0",
    description="五位基金经理的单人总结、多人综合与两轮会议讨论 API。",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FundScoreRequest(BaseModel):
    fund_input: str
    manager: str


@app.post("/api/funds/generate-score-prompt")
async def api_generate_score_prompt(data: FundScoreRequest, request: Request):

    clean_input = data.fund_input.strip()
    clean_manager = data.manager.strip()

    registry_state = request.app.state.registry

    if clean_manager not in registry_state.ids():
        raise HTTPException(
            status_code=422,
            detail=f"未找到该经理框架: {clean_manager}。当前可用: {', '.join(registry_state.ids())}"
        )

    try:
        result = generate_fund_prompt_service(
            fund_input=clean_input,
            manager=clean_manager,
            registry_state=registry_state
        )

        if isinstance(result, dict) and not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "生成打分提示词失败"))

        return result

    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"数据源映射缺失，未找到对应经理目录: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打分业务链内部发生未知故障: {str(e)}")




def _not_found(label: str, value: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{label}不存在：{value}")


@app.get("/api/managers")
async def list_managers(request: Request):
    return request.app.state.registry.list_public()


@app.get("/api/managers/{manager_id}")
async def get_manager(manager_id: str, request: Request):
    try:
        return request.app.state.registry.public(manager_id, include_detail=True)
    except KeyError:
        raise _not_found("基金经理", manager_id) from None


async def _settings(request: Request, refresh: bool = True) -> SettingsPublic:
    db = request.app.state.db
    gateway: DeepSeekGateway = request.app.state.gateway
    account: dict[str, Any] = {"available": None, "models": [], "balance_infos": []}
    if gateway.get_key() and refresh:
        try:
            account = await gateway.account_status()
        except Exception:
            account = {"available": False, "models": [], "balance_infos": []}
    return SettingsPublic(
        deepseek_configured=bool(gateway.get_key()),
        deepseek_key_masked=gateway.masked_key(),
        model=db.get_setting("model", "deepseek-v4-flash"),
        output_language=db.get_setting("output_language", "zh-CN"),
        summary_format=db.get_setting("summary_format", "structured"),
        api_available=account.get("available"),
        models=account.get("models", []),
        balance_infos=account.get("balance_infos", []),
        last_checked_at=db.get_setting("deepseek_last_checked_at"),
    )


@app.get("/api/settings", response_model=SettingsPublic)
async def get_settings(request: Request, refresh: bool = Query(True)):
    return await _settings(request, refresh)


@app.patch("/api/settings", response_model=SettingsPublic)
async def patch_settings(payload: SettingsPatch, request: Request):
    for key, value in payload.model_dump(exclude_none=True).items():
        request.app.state.db.set_setting(key, value)
    return await _settings(request, refresh=False)


@app.put("/api/settings/deepseek-key", response_model=SettingsPublic)
async def set_deepseek_key(payload: DeepSeekKeyInput, request: Request):
    request.app.state.gateway.set_key(payload.api_key)
    return await _settings(request, refresh=False)


@app.delete("/api/settings/deepseek-key", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deepseek_key(request: Request):
    request.app.state.gateway.delete_key()
    return Response(status_code=204)


@app.post("/api/settings/deepseek-test", response_model=SettingsPublic)
async def test_deepseek(request: Request):
    if not request.app.state.gateway.get_key():
        raise HTTPException(status_code=400, detail="请先保存 DeepSeek API Key")
    try:
        return await _settings(request, refresh=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 连接失败：{exc}") from exc


@app.get("/api/index/status", response_model=IndexStatus)
async def index_status(request: Request):
    return request.app.state.index.status()


@app.post("/api/index/rebuild", response_model=IndexStatus, status_code=status.HTTP_202_ACCEPTED)
async def rebuild_index(request: Request):
    task = request.app.state.index_task
    if task and not task.done():
        raise HTTPException(status_code=409, detail="索引正在构建")
    request.app.state.index_task = asyncio.create_task(_rebuild(request.app), name="manual-index-build")
    await asyncio.sleep(0)
    return request.app.state.index.status()


@app.get("/api/sources/{chunk_id}")
async def get_source(chunk_id: str, request: Request):
    try:
        return request.app.state.index.get_chunk(chunk_id)
    except KeyError:
        raise _not_found("引用片段", chunk_id) from None


@app.post("/api/threads", response_model=ThreadPublic, status_code=status.HTTP_201_CREATED)
async def create_thread(payload: ThreadCreate, request: Request):
    registry = request.app.state.registry
    unknown = [manager_id for manager_id in payload.manager_ids if manager_id not in registry.ids()]
    if unknown:
        raise HTTPException(status_code=422, detail=f"未知基金经理：{', '.join(unknown)}")
    if payload.mode.value == "single" and len(payload.manager_ids) != 1:
        raise HTTPException(status_code=422, detail="单人总结模式必须选择 1 位基金经理")
    if payload.mode.value in {"summary", "meeting"} and not 2 <= len(payload.manager_ids) <= 5:
        raise HTTPException(status_code=422, detail="多人总结和会议讨论模式必须选择 2–5 位基金经理")
    return request.app.state.db.create_thread(payload.mode, payload.manager_ids, payload.title)


@app.get("/api/threads", response_model=list[ThreadPublic])
async def list_threads(request: Request, search: str | None = Query(None)):
    return request.app.state.db.list_threads(search)


@app.get("/api/threads/{thread_id}", response_model=ThreadPublic)
async def get_thread(thread_id: str, request: Request):
    try:
        return request.app.state.db.get_thread(thread_id)
    except KeyError:
        raise _not_found("讨论线程", thread_id) from None


@app.delete("/api/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread_id: str, request: Request):
    try:
        request.app.state.db.delete_thread(thread_id)
    except KeyError:
        raise _not_found("讨论线程", thread_id) from None
    return Response(status_code=204)


@app.post("/api/threads/{thread_id}/runs", response_model=RunPublic, status_code=status.HTTP_202_ACCEPTED)
async def create_run(thread_id: str, payload: RunCreate, request: Request):
    try:
        request.app.state.db.get_thread(thread_id)
    except KeyError:
        raise _not_found("讨论线程", thread_id) from None
    if not request.app.state.gateway.get_key():
        raise HTTPException(status_code=409, detail="请先在设置中配置 DeepSeek API Key")
    index = request.app.state.index.status()
    if index["state"] not in {"ready", "degraded"}:
        raise HTTPException(status_code=409, detail="知识索引尚未就绪")
    return request.app.state.runs.create(
        thread_id, payload.question, request.app.state.db.get_setting("output_language", "zh-CN")
    )


@app.get("/api/runs/{run_id}", response_model=RunPublic)
async def get_run(run_id: str, request: Request):
    try:
        return request.app.state.db.get_run(run_id)
    except KeyError:
        raise _not_found("运行", run_id) from None


@app.get("/api/runs/{run_id}/events")
async def run_events(
        run_id: str,
        request: Request,
        last_event_id: str | None = Header(None, alias="Last-Event-ID"),
        after: int = Query(0, ge=0),
):
    try:
        request.app.state.db.get_run(run_id)
    except KeyError:
        raise _not_found("运行", run_id) from None
    cursor = int(last_event_id) if last_event_id and last_event_id.isdigit() else after
    return StreamingResponse(
        request.app.state.events.stream(run_id, cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/runs/{run_id}/cancel", response_model=ApiMessage)
async def cancel_run(run_id: str, request: Request):
    try:
        request.app.state.db.get_run(run_id)
    except KeyError:
        raise _not_found("运行", run_id) from None
    cancelled = await request.app.state.runs.cancel(run_id)
    if not cancelled:
        raise HTTPException(status_code=409, detail="运行已结束或不在当前进程中")
    return ApiMessage(message="运行已取消")


@app.get("/api/health")
async def health(request: Request):
    return {
        "status": "ok",
        "time": utcnow(),
        "managers": len(request.app.state.registry.ids()),
        "index": request.app.state.index.status()["state"],
    }
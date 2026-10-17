"""Disposable offline browser fixture. Real website/worker; fake lifecycle and RTC.

Never imported by the production website. No provider clients, credentials or Cloud.
"""

from __future__ import annotations

import ast
import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Request
from foodease_contract.startup import StartupBinding
from livekit.agents import AgentSession, APIConnectionError, llm, stt, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.voice.events import ErrorEvent
from livekit.agents.voice.io import TextOutput

ROOT = Path(__file__).resolve().parents[2]

from foodease_agent.adapters.integrated import IntegratedRpcAdapter  # noqa: E402
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent  # noqa: E402
from foodease_agent.integrated.runtime import LiveConversationRuntime  # noqa: E402
from foodease_agent.worker import run_integrated_job  # noqa: E402

from foodease_website.app import create_app  # noqa: E402
from foodease_website.config import load_settings  # noqa: E402

app = create_app(replace(load_settings(), orchestration_base_url="http://127.0.0.1:8186"))
generations: dict[str, dict] = {}


class LocalLLM(llm.LLM):
    def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
        return LocalStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=replace(conn_options, max_retry=0),
        )


class LocalStream(llm.LLMStream):
    async def _run(self):
        items = self._chat_ctx.items
        last = max(
            i
            for i, item in enumerate(items)
            if isinstance(item, llm.ChatMessage) and item.role == "user"
        )
        message = items[last]
        assert isinstance(message, llm.ChatMessage)
        user = (message.text_content or "").lower()
        if user == "offline provider failure":
            raise APIConnectionError("local fixture model unavailable")
        outputs = [item for item in items[last:] if isinstance(item, llm.FunctionCallOutput)]
        if outputs:
            # Installed SDK stringifies dict tool returns as Python literals.
            # Parse literals safely; this fixture never evals model/user content.
            try:
                result = json.loads(outputs[-1].output)
            except ValueError:
                result = ast.literal_eval(outputs[-1].output)
            text = (
                "Please review the summary above."
                if "summary_revision" in (result.get("facts") or {})
                else result.get("say", "What would you like next?")
            )
            delta = llm.ChoiceDelta(content=text)
            if (
                "find burgers then add" in user
                and len(outputs) == 1
                and result["status"] == "success"
            ):
                delta = llm.ChoiceDelta(
                    tool_calls=[
                        llm.FunctionToolCall(
                            name="cart_add_item",
                            call_id=uuid4().hex,
                            arguments=json.dumps({"item_id": "burger-veg", "quantity": 1}),
                        )
                    ]
                )
        else:
            if "find burgers then add" in user:
                name, args = "search_menu", {"query": "burger"}
            elif "spicy" in user:
                name, args = "filter_menu", {"tags": ["spicy"], "max_price_pkr": 950}
            elif "actually under" in user:
                name, args = "filter_menu", {"max_price_pkr": 600}
            elif "make it one" in user:
                name, args = "cart_set_quantity", {"item_id": "wrap-hot-chicken", "quantity": 1}
            elif "checkout" in user or "check out" in user:
                name, args = "checkout_get_summary", {}
            elif user.strip() == "yes":
                name, args = "checkout_submit_demo_order", {}
            elif "add" in user and "wrap" in user:
                name, args = (
                    "cart_add_item",
                    {"item_id": "wrap-hot-chicken", "quantity": 2 if "two" in user else 1},
                )
            elif "burger" in user:
                name, args = "search_menu", {"query": "burger"}
            else:
                name, args = "get_cart", {}
            delta = llm.ChoiceDelta(
                tool_calls=[
                    llm.FunctionToolCall(name=name, arguments=json.dumps(args), call_id=uuid4().hex)
                ]
            )
        self._event_ch.send_nowait(llm.ChatChunk(id=uuid4().hex, delta=delta))


class TextSink(TextOutput):
    def __init__(self):
        super().__init__(label="offline-browser-sink", next_in_chain=None)

    async def capture_text(self, text):
        pass

    def flush(self):
        pass


class Room:
    def __init__(self, record):
        self.record = record
        self.handlers = {}
        self.local_participant = self.person("agent")
        self.local_participant.perform_rpc = self.perform_rpc
        self.local_participant.publish_data = self.publish_data
        self.remote_participants = {role: self.person(role) for role in ("app", "user")}

    def person(self, role):
        return SimpleNamespace(
            identity=role,
            attributes={
                "foodease.role": role,
                "foodease.session": self.record["session_id"],
                "foodease.generation": self.record["generation"],
            },
        )

    def on(self, name, callback):
        self.handlers[name] = callback
        if name == "data_received" and self.record.get("context"):
            self.receive(self.record["context"], "foodease.context.v2", "app")

    def off(self, name, callback):
        self.handlers.pop(name, None)

    def receive(self, event, topic, role):
        if "data_received" in self.handlers:
            self.handlers["data_received"](
                SimpleNamespace(
                    data=json.dumps(event).encode(), topic=topic, participant=self.person(role)
                )
            )

    async def perform_rpc(self, *, destination_identity, method, payload, response_timeout):
        key = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.record["rpcs"][key] = future
        self.record["queue"].append(
            {"id": key, "method": method, "payload": payload, "callerIdentity": "agent"}
        )
        try:
            return await asyncio.wait_for(future, response_timeout)
        finally:
            self.record["rpcs"].pop(key, None)

    async def publish_data(self, raw, **kwargs):
        self.record["output"].append({"event": json.loads(raw), "topic": kwargs["topic"]})


@app.post("/v2/assist/start")
async def start(request: Request):
    sid = request.headers["X-FoodEase-Session"]
    owner = request.cookies["foodease_owner"]
    app.state.sessions.context(owner, sid)
    body = await request.json()
    generation = uuid4().hex
    binding = {
        "session_id": sid,
        "app_identity": "app",
        "user_identity": "user",
        "agent_identity": "agent",
    }
    record = {
        "schema_version": "2.0",
        "session_id": sid,
        "generation": generation,
        "request_id": body["request_id"],
        "binding": binding,
        "state": "preparing",
        "room": f"fake-{generation}",
        "livekit_url": "wss://offline.invalid",
        "tokens": {role: {"token": f"{sid}:{generation}:{role}"} for role in ("app", "user")},
        "queue": [],
        "rpcs": {},
        "output": [],
        "shutdown": [],
    }
    generations[sid] = record
    return {k: v for k, v in record.items() if k not in {"queue", "rpcs", "output", "shutdown"}}


@app.post("/v2/assist/ready")
async def ready(request: Request):
    sid = request.headers["X-FoodEase-Session"]
    record = generations[sid]
    record["state"] = "waiting_worker"
    room = record["rtc"] = Room(record)
    startup = StartupBinding(
        schema_version="2.0",
        transport="website",
        consent=True,
        generation=record["generation"],
        request_id=record["request_id"],
        binding=record["binding"],
        worker_proof="offline-fixture-proof",
    )

    async def connect(**kwargs):
        pass

    async def factory(ctx, metadata, gate):
        session = AgentSession(llm=LocalLLM(), max_tool_steps=8)
        session.output.transcription = TextSink()
        original = session.start

        async def local_start(*, agent, **kwargs):
            # Fake RTC has no WebRTC tracks. Keep the real SDK session/tools/LLM,
            # substituting only RoomIO attachment. This is not live media evidence.
            await original(agent=agent)

        session.start = local_start  # pyright: ignore[reportAttributeAccessIssue]
        runtime = LiveConversationRuntime(
            IntegratedFoodEaseAgent(), session, IntegratedRpcAdapter(gate), gate=gate
        )
        await runtime.prepare()
        record["runtime"] = runtime
        return runtime

    ctx = SimpleNamespace(
        room=room,
        connect=connect,
        add_shutdown_callback=record["shutdown"].append,
        shutdown=lambda reason: record.update(state="ended"),
        proc=SimpleNamespace(userdata={}),
    )
    record["worker"] = asyncio.create_task(
        run_integrated_job(ctx, startup, runtime_factory=factory)
    )
    return {"state": "waiting_worker"}


@app.post("/v2/assist/worker-ready")
async def worker_ready(request: Request):
    record = generations[(await request.json())["session_id"]]
    record["state"] = "active"
    return {
        k: record[k]
        for k in ("schema_version", "session_id", "generation", "request_id", "binding", "state")
    } | {"greeting_allowed": True}


@app.get("/v2/assist/status/{request_id}")
async def status(request: Request, request_id: str):
    return {"state": generations[request.headers["X-FoodEase-Session"]]["state"]}


@app.post("/v2/assist/end")
async def end(request: Request):
    record = generations.get(request.headers["X-FoodEase-Session"])
    body = await request.json()
    if (
        record
        and body["request_id"] == record["request_id"]
        and body.get("generation", record["generation"]) == record["generation"]
    ):
        record["state"] = "ended"
        for callback in record["shutdown"]:
            await callback()
    return {"state": "ended"}


@app.post("/_test/provider-error/{sid}/{component}")
async def provider_error(sid: str, component: str):
    # Real SDK event object and production handler; not a real vendor outage.
    error_type = {"stt": stt.STTError, "tts": tts.TTSError}[component]
    error = error_type(timestamp=1, label="local-fixture", error=TimeoutError(), recoverable=False)
    generations[sid]["runtime"].session.emit("error", ErrorEvent(error=error, source=object()))
    return {}


@app.post("/_test/forget-shopping/{sid}")
async def forget_shopping(sid: str):
    # Simulates retention loss. Unit tests separately construct a new SessionStore.
    app.state.sessions._sessions.pop(sid, None)
    return {}


@app.post("/_test/data/{sid}")
async def data(sid: str, request: Request):
    body = await request.json()
    record = generations[sid]
    if body["topic"] == "foodease.context.v2":
        record["context"] = body["event"]
    if record.get("rtc"):
        record["rtc"].receive(body["event"], body["topic"], body["role"])
    return {}


@app.get("/_test/poll/{sid}")
async def poll(sid: str, offset: int = 0):
    record = generations[sid]
    queue, record["queue"] = record["queue"], []
    return {"rpc": queue, "output": record["output"][offset:], "offset": len(record["output"])}


@app.post("/_test/result/{sid}/{key}")
async def rpc_result(sid: str, key: str, request: Request):
    future = generations[sid]["rpcs"].get(key)
    body = await request.json()
    if future is not None and not future.done():
        if body.get("error"):
            future.set_exception(RuntimeError("fake browser RPC rejected"))
        else:
            future.set_result(body["result"])
    return {}


@app.get("/_test/state/{sid}")
async def debug_state(sid: str):
    record = generations[sid]
    runtime = record.get("runtime")
    return {
        "state": record["state"],
        "mode": runtime.mode if runtime else None,
        "closed": runtime.closed if runtime else None,
        "turn": {
            key: getattr(runtime.active_turn, key)
            for key in ("id", "revision", "committed", "discarded")
        }
        if runtime and runtime.active_turn
        else None,
        "results": [
            {
                "operation": result.payload.operation,
                "status": result.payload.status,
                "error": result.payload.error_code,
            }
            for result in runtime.broker.results.values()
        ]
        if runtime
        else [],
        "output": record["output"][-12:],
    }

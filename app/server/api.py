from app.server.billing_service import BillingService
from app.server.cloud_service import CloudService
from app.server.license_service import LicenseService
from app.cloud.beatport_client import BeatportClient
from app.ai.graph_memory import GraphMemory
import time


license_service = LicenseService()
billing_service = BillingService()
cloud_service = CloudService()
beatport = BeatportClient()
graph = GraphMemory()
cached_model = None
cached_model_path = None

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except Exception:
    FastAPI = None
    BaseModel = object


class ActivateRequest(BaseModel):
    email: str
    license_key: str
    machine_id: str


class EntitlementsRequest(BaseModel):
    license: dict


class CheckoutRequest(BaseModel):
    plan: str
    email: str
    success_url: str = ""
    cancel_url: str = ""


class CloudRequest(BaseModel):
    plan: dict


class DownloadRequest(BaseModel):
    plan: dict


def create_app():

    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install fastapi and uvicorn to run API."
        )

    app = FastAPI(
        title="DJ AI OS Commercial API",
        version="0.1.0",
    )

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "service": "dj-ai-os-api",
        }

    @app.post("/activate")
    def activate(request: ActivateRequest):
        return license_service.activate(
            request.email,
            request.license_key,
            request.machine_id
        )

    @app.post("/entitlements")
    def entitlements(request: EntitlementsRequest):
        return license_service.entitlements_for_license(request.license)

    @app.post("/checkout")
    def checkout(request: CheckoutRequest):
        return billing_service.create_checkout(
            request.plan,
            request.email,
            request.success_url,
            request.cancel_url
        )

    @app.post("/cloud/packs")
    def cloud_packs(request: CloudRequest):
        return cloud_service.list_packs(request.plan)

    @app.post("/cloud/packs/{pack_id}/download")
    def cloud_pack_download(pack_id: str, request: DownloadRequest):
        return cloud_service.download_pack(pack_id, request.plan)

    @app.get("/charts/top100")
    def top100():
        data = beatport.top_100()
        return {"ok": True, "count": len(data) if isinstance(data, list) else 0, "items": data}

    class RecommendationRequest(BaseModel):
        dj_id: str | None = None
        genre: str | None = None

    @app.post("/recommendations")
    def recommendations(request: RecommendationRequest):
        charts = beatport.top_100()
        if isinstance(charts, dict) and charts.get("error"):
            return {"ok": False, "error": charts.get("error")}

        related = []
        if request.genre:
            related = [item for item in charts if request.genre.lower() in (item.get("release") or "").lower()]

        if not related:
            nodes = graph.summary().get("unknown_terms", [])
            related = [item for item in charts if any(n in ((item.get("title") or "") + " " + (item.get("artist") or "")).lower() for n in nodes)]

        if not related:
            related = charts[:10]

        return {"ok": True, "recommendations": related[:20]}

    @app.get("/graph/summary")
    def graph_summary():
        return {"ok": True, "summary": graph.summary()}

    @app.post("/graph/learn")
    def graph_learn(payload: dict):
        t = payload.get("text") or ""
        terms = graph.learn_from_text(t)
        return {"ok": True, "learned": terms}

    class GenerateBeatRequest(BaseModel):
        model_path: str | None = None
        bpm: int = 120
        bars: int = 4
        temperature: float = 1.0
        export_wav: bool = False

    @app.post("/generate-beat")
    def generate_beat(request: GenerateBeatRequest):
        try:
            from app.ai.beat_playback import play_generated_beat
            from app.ai.beat_playback import load_model
        except Exception as exc:
            return {"ok": False, "error": f"beat_playback import failed: {exc}"}

        export_path = None
        if request.export_wav:
            export_path = f"generated_beat_{int(time.time())}.wav"

        try:
            # if a cached model exists and no explicit model_path provided, use cached model
            model_path_to_use = request.model_path
            global cached_model, cached_model_path
            if not model_path_to_use and cached_model is not None:
                # pass the cached model by path indirection: beat_playback.load_model will handle None
                model_path_to_use = cached_model_path

            result = play_generated_beat(
                model_path=model_path_to_use,
                bpm=request.bpm,
                bars=request.bars,
                temperature=request.temperature,
                play=False,
                export_path=export_path,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "result": result}

    class LoadModelRequest(BaseModel):
        model_path: str

    @app.post("/load-model")
    def load_model_endpoint(req: LoadModelRequest):
        try:
            from app.ai.beat_playback import load_model
        except Exception as exc:
            return {"ok": False, "error": f"import failed: {exc}"}

        global cached_model, cached_model_path
        try:
            cached_model = load_model(req.model_path)
            cached_model_path = req.model_path
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "model_path": cached_model_path}

    @app.post("/unload-model")
    def unload_model_endpoint():
        global cached_model, cached_model_path
        cached_model = None
        cached_model_path = None
        return {"ok": True}

    @app.get("/model-status")
    def model_status():
        return {"ok": True, "loaded": cached_model is not None, "model_path": cached_model_path}

    class SubscribeRequest(BaseModel):
        email: str
        plan: str

    @app.post("/subscribe")
    def subscribe(req: SubscribeRequest):
        # Create a checkout and return provider URL placeholder
        checkout = billing_service.create_checkout(req.plan, req.email)
        if not checkout.get("ok"):
            return {"ok": False, "error": "checkout_failed"}
        return {"ok": True, "checkout": checkout}

    @app.get("/download/pack/{pack_id}")
    def download_pack(pack_id: str, license_sig: str | None = None):
        # Simple protection: require a valid signed license payload via query string 'license_sig' or header.
        # In production, use Authorization header and TLS, and validate server-side entitlements.
        license_header = license_sig
        if not license_header:
            return {"ok": False, "error": "MISSING_LICENSE"}

        # license data should be passed as JSON string signature; here we perform a naive verification
        try:
            import json
            license_data = json.loads(license_header)
        except Exception:
            return {"ok": False, "error": "INVALID_LICENSE_FORMAT"}

        if not license_service.verify(license_data):
            return {"ok": False, "error": "INVALID_LICENSE"}

        # if license ok, return pack metadata and a download URL (placeholder)
        # resolve pack via archive
        pack = None
        try:
            pack = cloud_service.archive.find_pack(pack_id)
        except Exception:
            pack = None

        if not pack:
            return {"ok": False, "error": "PACK_NOT_FOUND"}

        # return the cloud_service download response
        download_resp = cloud_service.download_pack(pack_id, {"licensed": True, "plan": "DJ_ARCHIVE", "entitlements": {"dj_archive_downloads": True}})
        if not download_resp.get("ok"):
            return {"ok": False, "error": download_resp.get("reason")}

        return {"ok": True, "pack": pack, "download": download_resp.get("download")}

    return app


if FastAPI is not None:
    app = create_app()
else:
    app = None

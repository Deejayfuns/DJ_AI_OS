"""
DJ AI OS — Commercial API

FastAPI application with license activation, entitlements, Stripe checkout,
webhooks, and admin API router.

Main entry: app.server.run:app
"""

import os
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.cloud.beatport_client import BeatportClient
from app.server.admin_api import router as admin_router, auth_router as admin_auth_router
from app.server.billing_service import BillingService
from app.server.cloud_service import CloudService
from app.server.deps import get_admin_token, get_session
from app.server.license_service import LicenseService
from app.cloud.dj_archive_cloud import DJArchiveCloud
from app.ai.graph_memory import GraphMemory
from app.server.rate_limit import RateLimitMiddleware


# ─── Request Models ───

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


class CustomerPortalRequest(BaseModel):
    stripe_customer_id: str
    return_url: str = ""


# ─── App ───

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="DJ AI OS Commercial API",
        version="0.1.0",
        description="License activation, billing, cloud, and admin API for DJ AI OS.",
    )

    # Rate limiting (abuse protection) — placed before CORS
    app.add_middleware(RateLimitMiddleware)

    # CORS (admin SPA dev + client)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include admin routers
    app.include_router(admin_router)        # /login, /config (token-verified)
    app.include_router(admin_auth_router)   # data/mutation (admin-only)

    # ─── Health ───

    @app.get("/health")
    async def health():
        return {"ok": True, "service": "dj-ai-os-api", "version": "0.1.0"}

    # ─── License Activation ───

    @app.post("/api/activate")
    async def activate(req: ActivateRequest, request: Request, session=Depends(get_session)):
        service = LicenseService(session)
        client_ip = request.client.host if request.client else None
        result = await service.activate(
            email=req.email,
            license_key=req.license_key,
            machine_id=req.machine_id,
            ip_address=client_ip,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason"))
        return result

    # ─── Entitlements ───

    @app.post("/api/entitlements")
    async def entitlements(req: EntitlementsRequest, session=Depends(get_session)):
        service = LicenseService(session)
        result = await service.entitlements_for_license_data(req.license)
        return result

    # ─── Checkout ───

    @app.post("/api/checkout")
    async def checkout(req: CheckoutRequest, session=Depends(get_session)):
        service = BillingService(session)
        result = await service.create_checkout(
            plan=req.plan, email=req.email, success_url=req.success_url, cancel_url=req.cancel_url
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason"))
        return result

    # ─── Customer Portal ───

    @app.post("/api/customer-portal")
    async def customer_portal(req: CustomerPortalRequest, session=Depends(get_session)):
        service = BillingService(session)
        result = await service.get_customer_portal_url(req.stripe_customer_id, req.return_url)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason"))
        return result

    # ─── Webhooks ───

    @app.post("/api/webhooks/stripe")
    async def webhook_stripe(request: Request, session=Depends(get_session)):
        raw_body = await request.body()
        sig_header = request.headers.get("Stripe-Signature", "")
        service = BillingService(session)
        result = await service.handle_webhook(raw_body, sig_header)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason"))
        return result

    # ─── Cloud Packs ───

    @app.post("/api/cloud/packs")
    async def cloud_packs(req: CloudRequest, session=Depends(get_session)):
        service = CloudService(session)
        return await service.list_packs(req.plan)

    # ─── Update Manifest ───

    @app.get("/api/update/manifest")
    async def update_manifest(
        version: str = None,
        channel: str = "stable",
        platform: str = "win32",
    ):
        """
        Return signed update manifest for the update engine.

        Client contract (UpdateEngine.check_for_updates):
        {
            "version": "0.2.0",
            "min_client_version": "0.1.0",
            "released_at": "2026-08-12T00:00:00Z",
            "critical": false,
            "changelog": "bug fixes",
            "download_url": "https://cdn.example.com/updates/v0.2.0",
            "modules": [
                {"name": "app/config/version.py", "version": "0.2.0", "sha256": "...", "size": 123, "hot_reload": false}
            ],
            "signature": "<ed25519_hex>"
        }

        The manifest file is expected at:
        - DJ_AI_OS_UPDATE_MANIFEST env var (file path), OR
        - ./update_manifest.json (repo root, for dev), OR
        - /app/update_manifest.json (container)
        """
        import json
        import os
        from pathlib import Path

        # Resolve manifest path
        manifest_path = os.environ.get("DJ_AI_OS_UPDATE_MANIFEST", "").strip()
        if not manifest_path:
            # Try common locations
            for candidate in [
                Path(__file__).resolve().parent.parent.parent / "update_manifest.json",
                Path("/app/update_manifest.json"),
            ]:
                if candidate.exists():
                    manifest_path = str(candidate)
                    break

        if not manifest_path or not Path(manifest_path).exists():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "reason": "MANIFEST_NOT_FOUND",
                    "message": "Update manifest not configured on server",
                }
            )

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "ok": False,
                    "reason": "MANIFEST_READ_ERROR",
                    "message": f"Failed to read manifest: {e}",
                }
            )

        # Basic schema validation (fail-closed)
        required_fields = ["version", "modules", "download_url", "signature"]
        for field in required_fields:
            if field not in manifest:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=500,
                    detail={
                        "ok": False,
                        "reason": "MANIFEST_INVALID",
                        "message": f"Manifest missing required field: {field}",
                    }
                )

        # Optional: filter modules by version/channel/platform if manifest supports it
        # For V1.0, return the full manifest as-is
        return manifest

    # ─── Update Module Artifact ───

    @app.get("/api/update/modules/{module_path:path}")
    async def update_module_artifact(module_path: str):
        """
        Serve a signed module artifact for the update engine.

        The update client resolves a module download URL as
        ``<download_url>/modules/<module_path>`` and fetches it here.
        ``download_url`` in the manifest is the server's base URL
        (e.g. ``https://api.dj-ai-os.example/api/update``), so the effective
        path is ``/api/update/modules/<module_path>``.

        Artifacts live in the directory configured by
        ``DJ_AI_OS_UPDATE_ARTIFACTS`` (default: ``dist/update_artifacts``),
        laid out by module name (e.g. ``app/config/version.py``).

        Path traversal is blocked: the resolved path MUST stay inside the
        artifacts root.
        """
        import os
        from pathlib import Path
        from fastapi import HTTPException
        from fastapi.responses import FileResponse

        artifacts_root = os.environ.get("DJ_AI_OS_UPDATE_ARTIFACTS", "").strip()
        if not artifacts_root:
            artifacts_root = os.path.join(
                Path(__file__).resolve().parent.parent.parent, "dist", "update_artifacts"
            )

        root = Path(artifacts_root).resolve()
        target = (root / module_path).resolve()

        # Path-traversal guard (fail-closed)
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"ok": False, "reason": "INVALID_MODULE_PATH"},
            )

        if not target.is_file():
            raise HTTPException(
                status_code=404,
                detail={"ok": False, "reason": "MODULE_NOT_FOUND"},
            )

        return FileResponse(
            str(target),
            media_type="application/octet-stream",
            filename=os.path.basename(target),
        )

    # ─── Cloud Download ───

    @app.post("/api/cloud/packs/{pack_id}/download")
    async def cloud_pack_download(pack_id: str, req: DownloadRequest, session=Depends(get_session)):
        service = CloudService(session)
        return await service.download_pack(pack_id, req.plan)

    # ─── Charts (Beatport) ───

    beatport = BeatportClient()
    graph = GraphMemory()

    @app.get("/charts/top100")
    async def top100():
        data = beatport.top_100()
        return {"ok": True, "count": len(data) if isinstance(data, list) else 0, "items": data}

    # ─── Recommendations ───

    class RecommendationRequest(BaseModel):
        dj_id: Optional[str] = None
        genre: Optional[str] = None

    @app.post("/charts/recommend")
    async def recommendations(req: RecommendationRequest):
        charts = beatport.top_100()
        if isinstance(charts, dict) and charts.get("error"):
            return {"ok": False, "error": charts.get("error")}

        related = []
        if req.genre:
            related = [
                item for item in charts if req.genre.lower() in (item.get("release") or "").lower()
            ]

        if not related:
            nodes = graph.summary().get("unknown_terms", [])
            related = [
                item
                for item in charts
                if any(
                    n in ((item.get("title") or "") + " " + (item.get("artist") or "")).lower()
                    for n in nodes
                )
            ]

        if not related:
            related = charts[:10]

        return {"ok": True, "recommendations": related[:20]}

    # ─── Admin SPA Static Files ───

    admin_build_dir = os.path.join(os.path.dirname(__file__), "..", "..", "admin", "build")
    admin_build_dir = os.path.abspath(admin_build_dir)

    if os.path.isdir(admin_build_dir):
        # Serve static assets
        assets_dir = os.path.join(admin_build_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/admin/assets", StaticFiles(directory=assets_dir), name="admin-assets")

        @app.get("/admin/{path:path}")
        async def serve_admin_spa(path: str):
            """Serve React SPA with client-side routing fallback to index.html."""
            file_path = os.path.join(admin_build_dir, path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # SPA fallback
            return FileResponse(os.path.join(admin_build_dir, "index.html"))

    return app


# ─── Entrypoint ───

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("DJ_AI_OS_API_PORT", "8000"))
    uvicorn.run(
        "app.server.api:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("DJ_AI_OS_API_RELOAD", "false").lower() == "true",
    )

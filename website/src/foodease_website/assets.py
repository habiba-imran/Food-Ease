"""Caching for public assets only; shopping/session endpoints keep their policy."""

from fastapi.staticfiles import StaticFiles


class PublicAssetFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        relative = path.replace(chr(92), "/")
        if response.status_code == 200:
            if relative.endswith(".webp"):
                response.headers["Content-Type"] = "image/webp"
            elif relative.endswith(".woff2"):
                response.headers["Content-Type"] = "font/woff2"
        if response.status_code in {200, 304}:
            if relative.startswith(("img/catalog-v7/", "img/editorial/fast-v7/")):
                # Never overwrite this versioned asset family; mint a new version instead.
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif relative.startswith("fonts/"):
                response.headers["Cache-Control"] = "public, max-age=86400"
        return response

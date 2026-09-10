"""
Custom storage for serving static files behind reverse proxy with subpath.
"""
from django.conf import settings

try:
    from whitenoise.storage import CompressedManifestStaticFilesStorage

    class SubpathStaticFilesStorage(CompressedManifestStaticFilesStorage):
        """
        Serves files from /static/ but generates URLs with the subpath prefix.

        Needed because nginx strips the subpath prefix before forwarding to Django,
        but templates must generate URLs like /meu-servico/static/...
        """
        manifest_strict = False

        def url(self, name):
            url = super().url(name)
            prefix = getattr(settings, 'FORCE_SCRIPT_NAME', '') or ''
            if prefix and not url.startswith(prefix):
                return prefix + url
            return url

except ImportError:
    from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

    class SubpathStaticFilesStorage(ManifestStaticFilesStorage):
        manifest_strict = False

        def url(self, name):
            url = super().url(name)
            prefix = getattr(settings, 'FORCE_SCRIPT_NAME', '') or ''
            if prefix and not url.startswith(prefix):
                return prefix + url
            return url

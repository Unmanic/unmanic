import base64
import tornado.web
import tornado.httpclient
from unmanic.libs.installation_link import Links


def resolve_proxy_target(target_id):
    """
    Finds the remote installation config based on target_id (name, address, or uuid).
    Returns a dict with 'url', 'auth_header' (dict), or None.
    """
    links = Links()
    remotes = links.settings.get_remote_installations()
    target_config = None

    # Helper to search remotes
    def search_remotes(search_list):
        if not target_id:
            return None
        t_id = str(target_id).strip().lower()
        # Priority 1: Address (normalized)
        for r in search_list:
            addr = str(r.get('address', '')).strip().lower().rstrip('/')
            if addr == t_id or addr == t_id.rstrip('/') or addr.replace('http://', '').replace('https://', '') == t_id.replace('http://', '').replace('https://', ''):
                return r
        # Priority 2: UUID
        for r in search_list:
            if str(r.get('uuid', '')).strip().lower() == t_id:
                return r
        # Priority 3: Name
        for r in search_list:
            if str(r.get('name', '')).strip().lower() == t_id:
                return r
        return None

    target_config = search_remotes(remotes)

    if not target_config:
        # Try reloading settings in case another process updated them
        links.settings.reload()
        remotes = links.settings.get_remote_installations()
        target_config = search_remotes(remotes)

    if not target_config:
        return None

    # Construct URL base
    url_base = target_config.get('address', '').rstrip('/')
    if not url_base.startswith('http'):
        url_base = 'http://' + url_base

    # Auth
    auth_headers = {}
    if target_config.get('auth') and target_config.get('auth').lower() == 'basic':
        username = target_config.get('username', '')
        password = target_config.get('password', '')
        auth_str = f"{username}:{password}"
        auth_bytes = auth_str.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        auth_headers['Authorization'] = f"Basic {base64_bytes.decode('ascii')}"

    return {
        'url_base': url_base,
        'headers':  auth_headers,
        'config':   target_config
    }


class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PATCH", "PUT", "OPTIONS")

    async def prepare(self):
        pass

    async def _handle_request(self, method):
        target_id = self.request.headers.get("X-Unmanic-Target-Installation")
        target_info = resolve_proxy_target(target_id)

        if not target_info:
            self.set_status(400)
            self.write(f"Unknown remote installation: {target_id}")
            return

        # Construct URL
        path = self.request.path
        if self.request.query:
            path += "?" + self.request.query

        url = f"{target_info['url_base']}{path}"

        # Prepare headers
        headers = self.request.headers.copy()
        for h in ['Host', 'Content-Length', 'Transfer-Encoding', 'Connection', 'X-Unmanic-Target-Installation']:
            if h in headers:
                del headers[h]

        # Add Auth
        headers.update(target_info['headers'])

        # Override Host to target? optional, but some servers require it matching
        # headers['Host'] = ...

        body = self.request.body if self.request.body else None

        client = tornado.httpclient.AsyncHTTPClient()
        try:
            response = await client.fetch(
                url,
                method=method,
                headers=headers,
                body=body,
                follow_redirects=False,
                raise_error=False
            )

            self.set_status(response.code)
            for k, v in response.headers.get_all():
                if k.lower() not in ['content-length', 'transfer-encoding', 'connection', 'server']:
                    self.set_header(k, v)

            if response.body:
                self.write(response.body)

        except Exception as e:
            self.set_status(502)
            self.write(f"Proxy Error: {str(e)}")

    async def get(self):
        await self._handle_request('GET')

    async def head(self):
        await self._handle_request('HEAD')

    async def post(self):
        await self._handle_request('POST')

    async def delete(self):
        await self._handle_request('DELETE')

    async def patch(self):
        await self._handle_request('PATCH')

    async def put(self):
        await self._handle_request('PUT')

    async def options(self):
        await self._handle_request('OPTIONS')

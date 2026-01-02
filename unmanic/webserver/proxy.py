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

    for r in remotes:
        if (r.get('name') == target_id or
                r.get('address') == target_id or
                r.get('uuid') == target_id):
            target_config = r
            break

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
        for h in ['Host', 'Content-Length', 'Transfer-Encoding', 'Connection']:
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

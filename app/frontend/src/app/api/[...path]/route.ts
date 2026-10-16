/**
 * Same-origin proxy: the browser calls /api/* on this server and we forward to
 * FastAPI. Doing it here (instead of a next.config rewrite) lets us:
 * - pass the browser's address in X-Forwarded-For, so the API's rate limits are
 *   per client rather than shared by everyone behind this server;
 * - read the API address at runtime instead of baking it in at build time;
 * - return a clear 502 when the API is unreachable instead of a bare 500;
 * - stream bodies both ways (uploads now, Server-Sent Events later).
 */

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 30_000;

// Hop-by-hop headers must not be forwarded (RFC 9110 §7.6.1); length and
// encoding are recomputed for the re-streamed body.
const DROP_REQUEST_HEADERS = ["host", "connection", "keep-alive", "transfer-encoding", "upgrade", "content-length"];
const DROP_RESPONSE_HEADERS = ["connection", "keep-alive", "transfer-encoding", "content-encoding", "content-length"];

async function proxy(request: Request, ctx: RouteContext<"/api/[...path]">): Promise<Response> {
  const { path } = await ctx.params;
  const incoming = new URL(request.url);
  const target = `${API_INTERNAL_URL}/api/${path.map(encodeURIComponent).join("/")}${incoming.search}`;

  const headers = new Headers(request.headers);
  for (const name of DROP_REQUEST_HEADERS) headers.delete(name);
  // Next.js sets x-forwarded-for from the socket address on incoming requests.
  const clientIp = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  if (clientIp) headers.set("x-forwarded-for", clientIp);
  headers.set("x-forwarded-host", incoming.host);
  headers.set("x-forwarded-proto", incoming.protocol.replace(":", ""));

  const hasBody = !["GET", "HEAD"].includes(request.method);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      // Required by Node's fetch when streaming a request body.
      ...(hasBody ? { duplex: "half" } : {}),
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(TIMEOUT_MS)]),
    } as RequestInit);
  } catch (error) {
    console.error(JSON.stringify({ event: "api_proxy.error", target, method: request.method, error: String(error) }));
    return Response.json(
      { detail: "The service is temporarily unavailable. Please try again." },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers(upstream.headers);
  for (const name of DROP_RESPONSE_HEADERS) responseHeaders.delete(name);
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export {
  proxy as DELETE,
  proxy as GET,
  proxy as HEAD,
  proxy as OPTIONS,
  proxy as PATCH,
  proxy as POST,
  proxy as PUT,
};

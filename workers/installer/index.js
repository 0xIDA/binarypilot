// BinaryPilot installer Worker — serves scripts/install.sh at the bare domain.
//
// Deploy:  cd workers/installer && npx wrangler deploy
// Bind:    in the Cloudflare dashboard attach the route `idor.lol/*` to this
//          worker (or set `routes` in wrangler.toml — see its comments).
//
// Behavior: GET / fetches scripts/install.sh from the upstream GitHub raw
// URL (pinned by path, not by tag — pushes to main self-update without a
// redeploy). Everything else 404s so the worker can't be used as an open
// proxy for arbitrary GitHub content.
//
// Cache: 60s at the edge so a viral tweet doesn't DDoS GitHub raw.

const UPSTREAM =
  "https://raw.githubusercontent.com/0xIDA/binarypilot/main/scripts/install.sh";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/" && url.pathname !== "/install.sh") {
      return new Response("not found", { status: 404 });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("method not allowed", { status: 405 });
    }

    const res = await fetch(UPSTREAM, {
      cf: { cacheTtl: 60, cacheEverything: true },
    });
    if (!res.ok) {
      return new Response(`upstream ${res.status}`, { status: 502 });
    }
    const body = await res.text();
    return new Response(body, {
      status: 200,
      headers: {
        "content-type": "text/x-shellscript; charset=utf-8",
        "cache-control": "public, max-age=60",
        "x-content-type-options": "nosniff",
      },
    });
  },
};

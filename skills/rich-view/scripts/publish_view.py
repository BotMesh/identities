#!/usr/bin/env python3
"""Publish an HTML report to S3-compatible storage (Cloudflare R2 / MinIO)
and return a presigned URL that expires after a short TTL.

Pure stdlib: implements AWS SigV4 query presigning (no boto3).

Env:
  RICH_VIEW_S3_ENDPOINT  e.g. https://<account>.r2.cloudflarestorage.com
                         or   http://minio.internal:9000
  RICH_VIEW_S3_BUCKET    bucket name (path-style addressing is used)
  RICH_VIEW_S3_KEY_ID    access key id
  RICH_VIEW_S3_SECRET    secret access key
  RICH_VIEW_S3_REGION    default "auto" (R2); use "us-east-1" for MinIO
  RICH_VIEW_TTL_SECONDS  presigned-GET lifetime, default 86400 (1 day);
                         SigV4 maximum is 604800 (7 days)

Usage:
  publish_view.py --file report.html            # upload + print URL JSON
  publish_view.py --self-test                   # verify signer vs AWS vector
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request


def _hmac(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def presign(method, endpoint, region, key_id, secret, path, expires,
            now=None, extra_query=None):
    """Return a SigV4 query-presigned URL for `method` on endpoint+path."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    scope = f"{datestamp}/{region}/s3/aws4_request"
    query = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{key_id}/{scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-SignedHeaders": "host",
    }
    query.update(extra_query or {})
    canonical_query = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(query.items()))
    canonical_request = "\n".join([
        method,
        urllib.parse.quote(path),
        canonical_query,
        f"host:{host}\n",
        "host",
        "UNSIGNED-PAYLOAD",
    ])
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])
    signing_key = _hmac(_hmac(_hmac(_hmac(
        ("AWS4" + secret).encode(), datestamp), region), "s3"), "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode(),
                         hashlib.sha256).hexdigest()
    return (f"{parsed.scheme}://{host}{urllib.parse.quote(path)}"
            f"?{canonical_query}&X-Amz-Signature={signature}")


def self_test():
    """Reproduce the official AWS SigV4 presigning example.

    https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-query-string-auth.html
    GET test.txt from examplebucket, us-east-1, 86400s, 20130524T000000Z.
    """
    url = presign(
        "GET", "https://examplebucket.s3.amazonaws.com", "us-east-1",
        "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "/test.txt", 86400,
        now=datetime.datetime(2013, 5, 24, 0, 0, 0,
                              tzinfo=datetime.timezone.utc))
    expected = ("aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f60"
                "4d404")
    got = url.rsplit("X-Amz-Signature=", 1)[1]
    if got == expected:
        print(json.dumps({"ok": True, "self_test": "signature matches the "
                          "official AWS SigV4 test vector"}))
        return 0
    print(json.dumps({"ok": False, "expected": expected, "got": got}))
    return 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file")
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.file:
        p.error("--file is required")

    endpoint = os.environ.get("RICH_VIEW_S3_ENDPOINT")
    bucket = os.environ.get("RICH_VIEW_S3_BUCKET")
    key_id = os.environ.get("RICH_VIEW_S3_KEY_ID")
    secret = os.environ.get("RICH_VIEW_S3_SECRET")
    region = os.environ.get("RICH_VIEW_S3_REGION", "auto")
    ttl = min(int(os.environ.get("RICH_VIEW_TTL_SECONDS", "86400")), 604800)
    if not all([endpoint, bucket, key_id, secret]):
        print(json.dumps({"ok": False, "error":
                          "RICH_VIEW_S3_* env not configured — fall back to a "
                          "plain-text table in the chat message"}))
        sys.exit(1)

    body = open(a.file, "rb").read()
    obj = f"/{bucket}/r-{secrets.token_urlsafe(16)}.html"

    put_url = presign("PUT", endpoint, region, key_id, secret, obj, 300)
    req = urllib.request.Request(put_url, data=body, method="PUT",
                                 headers={"Content-Type":
                                          "text/html; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201):
            print(json.dumps({"ok": False, "error": f"upload HTTP {resp.status}"}))
            sys.exit(1)

    get_url = presign("GET", endpoint, region, key_id, secret, obj, ttl)
    print(json.dumps({"ok": True, "url": get_url, "expires_in_seconds": ttl,
                      "note": "link stops working after expiry; the object "
                              "itself is removed by the bucket lifecycle rule"}))


if __name__ == "__main__":
    main()

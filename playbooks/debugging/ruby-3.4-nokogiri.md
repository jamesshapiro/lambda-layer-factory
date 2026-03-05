# Debugging: Ruby 3.4 Nokogiri SSL on Lambda

## Problem
Ruby 3.3 + Nokogiri layer works with `SSL_CERT_FILE` env var.
Ruby 3.4 + Nokogiri layer fails with the same env var, same cert path.

**Error:** `SSL_connect returned=1 errno=0 ... certificate verify failed (unable to get local issuer certificate)`

## Layer ARNs
- 3.3: `arn:aws:lambda:us-east-1:306468203480:layer:rb-33-nokogiri-lf:1` (working)
- 3.4: `arn:aws:lambda:us-east-1:306468203480:layer:rb-34-nokogiri-lf:1` (broken)

Both use Nokogiri 1.19.0.

## What we checked

### 1. Cert files exist on the 3.4 runtime
- `/etc/pki/tls/certs/ca-bundle.crt` — exists
- `/etc/pki/tls/cert.pem` — exists
- `SSL_CERT_FILE` env var is set correctly

### 2. OpenSSL defaults differ from env var
- `OpenSSL::X509::DEFAULT_CERT_FILE` = `/etc/pki/tls/cert.pem`
- `OpenSSL::X509::DEFAULT_CERT_DIR` = `/etc/pki/tls/certs`
- `ENV['SSL_CERT_FILE']` = `/etc/pki/tls/certs/ca-bundle.crt`

Both files exist, so the default path isn't the issue either.

### 3. Runtime info
- Ruby 3.4.8
- Nokogiri 1.19.0
- Runtime is AL2023 (Ruby 3.4 uses AL2023, 3.3 uses AL2)

## Hypothesis
Nokogiri bundles its own OpenSSL. The 3.4 build may have a bundled OpenSSL that:
- Ignores the `SSL_CERT_FILE` env var
- Uses its own compiled-in cert path that doesn't exist on Lambda
- Or has a version mismatch with the system libssl

## Next step
Deploy a debug Lambda that:
1. Tries `Net::HTTP.get_response` with default settings (the failing path)
2. Tries with explicit `http.ca_file = '/etc/pki/tls/certs/ca-bundle.crt'`
3. Reports `OpenSSL::OPENSSL_VERSION` and `OpenSSL::OPENSSL_LIBRARY_VERSION`

This will tell us if explicitly setting ca_file works (env var being ignored)
and whether the OpenSSL version is the system one or Nokogiri's bundled one.

## Results: Debug invoke #1

Both default `get_response` and explicit `ca_file` fail with the same error.

```json
{
    "default_error": "OpenSSL::SSL::SSLError: certificate verify failed (unable to get local issuer certificate)",
    "explicit_ca_error": "OpenSSL::SSL::SSLError: certificate verify failed (unable to get local issuer certificate)",
    "openssl_version": "OpenSSL 3.2.2 4 Jun 2024",
    "openssl_library_version": "OpenSSL 3.2.2 4 Jun 2024",
    "ruby_version": "3.4.8"
}
```

**Key finding:** `openssl_version` and `openssl_library_version` match — this is Nokogiri's
bundled OpenSSL 3.2.2, not the system one. The bundled OpenSSL can't verify the system CA
bundle even when explicitly pointed at it.

## Next step: Debug invoke #2

Trying four approaches:
1. `ca_file = ca-bundle.crt`
2. `ca_file = cert.pem` (OpenSSL's compiled default)
3. Manual `OpenSSL::X509::Store` loaded from ca-bundle.crt
4. `VERIFY_NONE` (confirm network connectivity works at all)
Also counting certs in the bundle to rule out an empty/corrupt file.

## Results: Debug invoke #2

```json
{
    "ca_bundle_error": "certificate verify failed (unable to get local issuer certificate)",
    "cert_pem_error": "certificate verify failed (unable to get local issuer certificate)",
    "manual_store_error": "certificate verify failed (unable to get local issuer certificate)",
    "no_verify": "OK: 200",
    "cert_read_error": "invalid byte sequence in US-ASCII",
    "openssl_version": "OpenSSL 3.2.2 4 Jun 2024",
    "ruby_version": "3.4.8"
}
```

**Key findings:**
- `VERIFY_NONE` works — network connectivity is fine, it's purely a cert verification issue
- All three cert approaches fail (ca_file, cert.pem, manual store)
- `cert_read_error: "invalid byte sequence in US-ASCII"` — Ruby 3.4 can't even read the cert
  file with default encoding. Suggests the Lambda runtime has LANG/LC_ALL unset or set to
  US-ASCII, and Ruby 3.4 is stricter about encoding than 3.3.
- OpenSSL's C-level `add_file` also fails, so the encoding issue may affect the C layer too,
  or Nokogiri's bundled OpenSSL 3.2.2 has a different trust store format expectation.

## Next step: Debug invoke #3

Checking `Encoding.default_external`, `LANG`, `LC_ALL` env vars to confirm locale theory.
Also reading cert bundle with explicit binary encoding to get cert count/size.

## Results: Debug invoke #3 — shared library check

```json
{
    "loaded_ssl_libs": ["/usr/lib64/libcrypto.so.3.2.2", "/usr/lib64/libssl.so.3.2.2"],
    "opt_lib_files": [],
    "ld_library_path": "/var/lang/lib:...:/opt/lib"
}
```

**Hypothesis disproven:** Nokogiri does NOT bundle OpenSSL in this layer. It's using the
system OpenSSL 3.2.2 from `/usr/lib64/`. No conflicting libraries.

## Results: Debug invoke #4 — cert chain inspection

```json
{
    "peer_chain": ["example.com", "Cloudflare TLS Issuing ECC CA 3", "SSL.com TLS Transit ECC CA R2"],
    "peer_issuer": ["Cloudflare TLS Issuing ECC CA 3", "SSL.com TLS Transit ECC CA R2", "AAA Certificate Services"],
    "root_trusted": false,
    "default_paths_error": "certificate verify failed"
}
```

**Key finding:** The chain ends at `SSL.com TLS Transit ECC CA R2`, signed by
`AAA Certificate Services` (Comodo root). That root is NOT in the chain — must be in the
trust store. But the store says `root_trusted: false`.

Even `set_default_paths` (OpenSSL's own cert discovery) fails. This means the system
OpenSSL 3.2.2 on AL2023/Ruby 3.4 can't verify ANY certs via the standard paths.

## Next step: Debug invoke #5

1. Is "AAA Certificate Services" actually in the cert bundle?
2. Do non-Cloudflare URLs (aws.amazon.com, httpbin.org) also fail?

## Results: Debug invoke #5 — ROOT CAUSE FOUND

```json
{
    "has_aaa_cert": false,
    "aaa_cert_subjects": [],
    "example.com": "FAIL: certificate verify failed",
    "aws.amazon.com": "OK: 200",
    "httpbin.org": "OK: 200"
}
```

## Root Cause

**The `AAA Certificate Services` (Comodo) root CA is NOT in the AL2023 cert bundle.**

- Ruby 3.3 runs on AL2, which includes this root CA → SSL works for example.com
- Ruby 3.4 runs on AL2023, which removed it → SSL fails for example.com
- Other URLs (aws.amazon.com, httpbin.org) work fine on 3.4

**This is NOT a Nokogiri problem.** It's not an OpenSSL problem. It's not an env var problem.
It's simply that example.com (Cloudflare) uses a cert chain rooted in a CA that AL2023
no longer trusts.

## Resolution

Use a different test URL (e.g. `https://aws.amazon.com`). Ruby 3.4 + Nokogiri layer works.

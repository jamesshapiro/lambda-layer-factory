# lambda-layer-factory

Utilities to make it easier to create Lambda Layers

## Validated Runtimes

- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13 (tested with requests)
- **Ruby**: 3.3, 3.4 (tested with Nokogiri)

## Notes

**Ruby + Nokogiri SSL:** If your layer includes Nokogiri, add this environment variable to your Lambda function:

```
SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
```

Without this, HTTPS requests will fail with `certificate verify failed`.
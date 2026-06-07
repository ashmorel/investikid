# Apple Root CA certificates

`apple_billing_service._build_verifier()` loads every `*.cer` file in this
directory as trust roots for verifying Apple's signed JWS payloads
(StoreKit transactions and App Store Server Notifications).

## What the operator must do

Download Apple's Root CA certificates from
<https://www.apple.com/certificateauthority/> and drop the DER-encoded `.cer`
files into this directory. At minimum you need:

- **Apple Root CA - G3** (used for StoreKit / App Store Server signing)

Place any required intermediate certificates here too. Files are loaded in
sorted filename order; the filenames themselves do not matter beyond the
`.cer` extension.

## Notes

- The binary `.cer` files are **not** committed to the repo — each deployment
  environment must provide them (e.g. baked into the image or mounted).
- Unit tests monkeypatch `_build_verifier`, so they do not require these certs.
- If this directory contains no `.cer` files in production, JWS verification
  will fail — make sure the certificates are present before going live.

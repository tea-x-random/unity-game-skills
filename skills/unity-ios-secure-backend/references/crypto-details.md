# Crypto details — exact byte layouts

Everything here is grounded in `real-app-attest.verifier.ts` and `real-game-center.verifier.ts`. These are the byte-level facts you cannot get wrong, or verification silently fails.

## Game Center identity — the signed payload

Verifier: `RealGameCenterVerifier.buildSignedPayload` + `verify`.

```
signedPayload = playerId(UTF-8)
              || bundleId(UTF-8)
              || timestamp        (big-endian uint64, MILLISECONDS)
              || salt             (raw bytes; transported base64)
signatureAlg  = RSA-SHA256
publicKey     = cert downloaded from publicKeyURL (https, *.apple.com host, validity-window checked)
```

- `timestamp` is **milliseconds** and **8 bytes big-endian** (`writeBigUInt64BE`). Seconds, or little-endian, → every signature fails.
- `salt` arrives base64 in `X-GC-Salt`; decode to raw bytes before concatenating.
- **Try every candidate `playerId`** (primary + `X-GC-Player-Id-Alt` split on commas, trimmed, de-duped) until `verify` returns true; derive the stable `userId` from whichever id verified. Apple signs over exactly one id, but which one (teamPlayerID / gamePlayerID / legacy) varies by iOS version.
- Reject stale timestamps (replay): `|now - timestamp| > GC_MAX_TIMESTAMP_AGE_SECONDS*1000`.
- `publicKeyURL` must be `https:` on an allowed host (`apple.com` or `*.apple.com`); cache the fetched cert (~1h).

## App Attest — `authData` layout

`parseAuthData` (attestation) / `parseAssertionAuthData` (assertion):

```
offset  bytes  field
0       32     rpIdHash               = SHA256(appId), appId = "{TEAM_ID}.{BUNDLE_ID}"
32      1      flags
33      4      signCount              (uint32 big-endian)
--- attested credential data (attestation only) ---
37      16     aaguid                 ("appattestdevelop" => development; "appattest\0..." => production)
53      2      credIdLen              (uint16 big-endian)
55      N      credentialId           (= SHA256(uncompressed EC point); N is 32 for App Attest)
```

Assertion `authenticatorData` has **no** attested-credential-data — only `rpIdHash(32) flags(1) signCount(4)`.

## App Attest — the nonce (request binding)

```
clientDataHash = SHA256( UTF8("POST\n/api/scores/submit\n") + SHA256(rawBodyBytes) )
nonce          = SHA256( authData || clientDataHash )
```

`nonce` must equal the nonce embedded in the credential cert (attestation) / be re-derived and the assertion `signature` verified over it (assertion). The cert nonce lives under extension OID `1.2.840.113635.100.8.2`.

### OID DER — the 9-vs-10 byte trap

```
OID 1.2.840.113635.100.8.2
content bytes (9):  2a 86 48 86 f7 63 64 08 02
full DER:           06 09 2a 86 48 86 f7 63 64 08 02
                    ^^ ^^  tag=06 (OID), length=09  (NOT 0a/10)
```

Search the cert's raw DER for the **9 content bytes** (`indexOf`), prefix-independent — never search `06 0a …` (that's length 10 and never matches → null nonce → `request_hash_mismatch` on every request). After locating the OID, scan forward (bounded, ~200 bytes) for the OCTET-STRING-of-32 marker:

```
04 20  <32 nonce bytes>
^^ ^^  tag=04 (OCTET STRING), length=0x20=32
```

Take the 32 bytes after `04 20` as the cert nonce.

## App Attest — keyId / credentialId derivation

```
rawPoint     = 0x04 || X || Y        (uncompressed X9.63 EC point; 65 bytes for P-256)
keyId        = SHA256(rawPoint)      (== credentialId in authData, == base64 of X-App-Attest-Key-Id)
```

- `rawPoint` is the `SecKeyCopyExternalRepresentation` form. Build it from the cert public key's JWK `x`/`y` (base64url-decoded): `Buffer.concat([Buffer.from([0x04]), x, y])`.
- Do **NOT** hash the SPKI DER (`export({format:'der',type:'spki'})`) — that never equals `credentialId`. The SPKI DER is what you **store** (`appAttestKeys.publicKey`, base64) to verify future assertions with `createPublicKey({key, format:'der', type:'spki'})`.

## App Attest — cert chain + environment

- `x5c[0]` = credential cert, `x5c[1]` = intermediate. Verify `intermediate` against the **real Apple App Attest Root CA**, then `credCert` against the intermediate.
- Root CA PEM: store as an array of lines `.join('\n')` (immune to CRLF), not a template literal.
- `aaguid` (16 bytes at offset 37) → environment: `"appattestdevelop"` = development, anything starting `"appattest"` (trailing NULs) = production. Must equal `APP_ATTEST_ENV` (`production` for TestFlight/App Store).
- `rpIdHash` must equal `SHA256(appId)` where `appId = "{APPLE_TEAM_ID}.{APP_BUNDLE_ID}"`.

## Assertion verification

```
nonce = SHA256(authData || clientDataHash)
verify: createVerify('SHA256').update(nonce) -> verify(storedSpkiPublicKey, assertion.signature)
```

Then re-check `rpIdHash == SHA256(appId)` and enforce the strictly-increasing `signCount` with a guarded `UPDATE ... WHERE signCount < newCount` (replay rejection).

## Server diagnostic on `request_hash_mismatch`

The verifier logs/returns: `cdh=<base64 clientDataHash> cert=<first 12 hex of cert nonce | NULL> nonce=<first 12 hex of computed> adLen=<authData length>`.

- `cert=NULL` → OID/nonce extraction failed (the `04 20` / 9-byte OID bug), NOT a body mismatch.
- `cert` present but `!= nonce`, and the client's `LastClientHash != cdh` → the bodies differ (re-serialization, missing raw-body capture, extra field).
- `cdh` equals the client's `LastClientHash` but still mismatch → cert extraction issue, not the body.

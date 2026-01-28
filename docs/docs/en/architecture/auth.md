# Authentication Architecture

This document describes the architectural decisions behind the Lazy Ninja authentication system.

It focuses on *why* things work the way they do, the trade-offs involved, and the constraints the project operates under.

This is **not** a usage guide.
For step-by-step instructions, see the Authentication Guide.

---

## Context

Lazy Ninja is a generic backend library designed to work across
many different Django projects and domains.

Because of that, authentication cannot be treated as a
one-size-fits-all solution.

Different applications have different needs:

- Internal tools vs public APIs
- Small apps vs distributed systems
- Low-risk vs high-security domains
- Stateless vs stateful infrastructures

The authentication system is designed to **adapt**, not to dictate.

---

## Goals

The authentication module aims to:

- Work across a wide range of backend projects
- Integrate naturally with Django and Django Ninja
- Support both stateless and stateful authentication models
- Avoid forcing OAuth/OIDC or external identity providers
- Provide sensible defaults with clear escape hatches
- Be extensible without forking the library

---

## Non-goals

The authentication module does **not** aim to:

- Replace Django’s authentication system
- Be a full IAM or identity provider
- Enforce a single “best” authentication strategy
- Cover every possible security model out of the box
- Hide architectural trade-offs from developers

Lazy Ninja prefers *explicit decisions* over *magical abstractions*.

---

## Stateless vs Stateful Authentication

### Stateless Mode (default)

In stateless mode:

- Tokens are self-contained (JWT)
- The server does not store session state
- Token validity is verified cryptographically
- Logout is a client-side concern

**Advantages:**
- Horizontally scalable
- No shared session storage
- Simple infrastructure
- Ideal for APIs and microservices

**Trade-offs:**
- Tokens cannot be revoked immediately
- Logout does not invalidate existing tokens
- Security relies on expiration times

Stateless mode is suitable for:
- Public APIs
- Mobile clients
- SPAs
- Distributed systems

---

### Stateful Mode (optional)

In stateful mode:

- Tokens include a `jti` (JWT ID)
- Tokens can be revoked server-side
- A cache-backed blacklist is used
- Logout invalidates tokens immediately

**Advantages:**
- Immediate revocation
- Stronger security guarantees
- Better auditability

**Trade-offs:**
- Requires shared cache (Redis, Memcached, etc.)
- Slightly higher operational complexity
- Reduced horizontal simplicity

Stateful mode is suitable for:
- Admin dashboards
- High-security applications
- Regulated environments

Lazy Ninja allows switching between these modes without breaking clients.

---

## Why JWT

JWTs were chosen because they:

- Are widely supported
- Work well with HTTP APIs
- Integrate naturally with Django Ninja
- Allow stateless verification
- Can be extended for stateful revocation

JWT is not presented as a perfect solution,
but as a **practical and well-understood one**.

---

## Access Tokens vs Refresh Tokens

Lazy Ninja uses two token types:

- **Access tokens**: short-lived, used on every request
- **Refresh tokens**: long-lived, used only to mint new access tokens

This separation limits exposure while keeping usability high.

---

## Why JWT for Refresh Tokens

Using JWTs for refresh tokens is a **deliberate architectural choice**.

### Why it works

- Keeps the system consistent
- Avoids introducing a second token format
- Enables stateless or stateful flows
- Supports rotation and revocation
- Reduces storage requirements in stateless mode

### Trade-offs

- Stateless refresh tokens cannot be revoked instantly
- Requires rotation or stateful mode for stronger guarantees

Lazy Ninja addresses these trade-offs by:

- Supporting refresh token rotation
- Allowing stateful revocation via `jti`
- Making the choice explicit and configurable

There is no universal “correct” approach — only domain-driven decisions.

---

## Token Claims

Lazy Ninja uses standard JWT claims to enforce boundaries:

- `iss` (Issuer): identifies who issued the token
- `aud` (Audience): restricts where the token is valid
- `exp` (Expiration): limits token lifetime
- `iat` (Issued At): audit and ordering
- `jti` (JWT ID): enables revocation in stateful mode
- `sub` (Subject): identifies the user

Issuer and audience are always validated to prevent token reuse across systems.

---

## Token Rotation

Refresh token rotation is enabled by default.

When a refresh token is used:

- A new refresh token is issued
- The previous refresh token can be blacklisted (stateful mode)

This limits replay attacks and reduces the impact of token leakage.

---

#

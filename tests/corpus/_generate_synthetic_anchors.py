"""One-shot generator for tests/corpus/synthetic_anchors/.

Each anchor is a directory with `code.tsx` (or `code.ts`) and `manifest.json`.

Anchors are EXTREME by design: a competent React/RN engineer should agree on
the score within ±1. Mid-range examples (4-7) are deliberately NOT included
— that zone needs human ground truth to be reliable.

Run:
    python tests/corpus/_generate_synthetic_anchors.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent / "synthetic_anchors"
ROOT.mkdir(parents=True, exist_ok=True)


# (slug, iso_sub_id, expected_score, tier, framework, code, justification)
Anchor = Tuple[str, str, int, str, str, str, str]

ANCHORS: List[Anchor] = [
    # ---------------- Security / Confidentiality ----------------
    (
        "ISO_SEC_CONF_score_01_hardcoded_prod_secret",
        "ISO_SEC_CONF", 1, "extreme_low", "react",
        '''const STRIPE_SECRET = "EXAMPLE_FAKE_PROD_SECRET_PLACEHOLDER_xxxxxxxxxxxx";
export async function charge(amount: number) {
  return fetch("https://api.stripe.com/v1/charges", {
    method: "POST",
    headers: { Authorization: `Bearer ${STRIPE_SECRET}` },
    body: new URLSearchParams({ amount: String(amount) }),
  });
}
''',
        "Hardcoded production payment-processor secret in client source "
        "(value here is an obvious placeholder; the smell is the pattern: "
        "secret-shaped string assigned to a const named with an authn-secret "
        "keyword, embedded in client-shipped code). Catastrophic.",
    ),
    (
        "ISO_SEC_CONF_score_02_token_in_localstorage",
        "ISO_SEC_CONF", 2, "extreme_low", "react",
        '''import { useEffect } from "react";
export function App() {
  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then(r => r.json())
      .then(({ jwt }) => localStorage.setItem("authToken", jwt));
  }, []);
  return null;
}
''',
        "Auth JWT in localStorage is extractable by any XSS. httpOnly cookies "
        "or memory + refresh are the established patterns.",
    ),
    (
        "ISO_SEC_CONF_score_09_keychain_with_biometry",
        "ISO_SEC_CONF", 9, "extreme_high", "react-native",
        '''import * as Keychain from "react-native-keychain";

export async function saveToken(user: string, token: string) {
  await Keychain.setGenericPassword(user, token, {
    service: "com.acme.auth",
    accessible: Keychain.ACCESSIBLE.WHEN_PASSCODE_SET_THIS_DEVICE_ONLY,
    accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET,
  });
}

export async function loadToken(): Promise<string | null> {
  const creds = await Keychain.getGenericPassword({ service: "com.acme.auth" });
  return creds ? creds.password : null;
}
''',
        "OS keychain + biometry + passcode-set-this-device-only is the "
        "highest-tier mobile auth-token storage available. Cannot be "
        "extracted without device unlock + biometric.",
    ),
    # ---------------- Security / Integrity ----------------
    (
        "ISO_SEC_INT_score_01_dangerously_set_inner_html_user_content",
        "ISO_SEC_INT", 1, "extreme_low", "react",
        '''export function Comment({ html }: { html: string }) {
  return <article dangerouslySetInnerHTML={{ __html: html }} />;
}
''',
        "User-supplied HTML rendered directly to DOM with no sanitization. "
        "Textbook reflected XSS.",
    ),
    (
        "ISO_SEC_INT_score_02_eval_on_user_input",
        "ISO_SEC_INT", 2, "extreme_low", "react",
        '''export function Calculator({ formula }: { formula: string }) {
  const result = eval(formula);
  return <p>{result}</p>;
}
''',
        "eval() on user input executes arbitrary JS. Indefensible.",
    ),
    (
        "ISO_SEC_INT_score_09_strict_zod_at_boundaries",
        "ISO_SEC_INT", 9, "extreme_high", "react",
        '''import { z } from "zod";

const Review = z.object({
  id: z.string().uuid(),
  author: z.string().min(1).max(80),
  body: z.string().max(2000),
  rating: z.number().int().min(1).max(5),
});

export type Review = z.infer<typeof Review>;

export async function fetchReview(id: string): Promise<Review> {
  const res = await fetch(`/api/reviews/${encodeURIComponent(id)}`);
  return Review.parse(await res.json());
}

export function ReviewView({ review }: { review: Review }) {
  return <article><h3>{review.author}</h3><p>{review.body}</p></article>;
}
''',
        "Schema-first parsing at the boundary. Types derived from Zod. "
        "Output rendered via React text node (auto-escaped). High integrity.",
    ),
    # ---------------- Security / Authenticity ----------------
    (
        "ISO_SEC_AUTH_score_01_route_guard_only_in_ui",
        "ISO_SEC_AUTH", 1, "extreme_low", "react",
        '''import { useAuth } from "./auth";
export function AdminPage() {
  const { user } = useAuth();
  if (!user?.isAdmin) return <p>access denied</p>;
  return <UserList />;
}
function UserList() {
  return <ul />;
}
''',
        "Authorization decided in the UI. Anyone can call the underlying API "
        "directly. The guard is decorative.",
    ),
    (
        "ISO_SEC_AUTH_score_09_oidc_with_pkce_and_refresh",
        "ISO_SEC_AUTH", 9, "extreme_high", "react",
        '''import { authClient } from "./auth-client";  // wraps oidc-client-ts

export async function login() {
  await authClient.signinRedirect({
    response_type: "code",
    code_challenge_method: "S256",
    scope: "openid profile email offline_access",
  });
}

export async function callApi(path: string) {
  const user = await authClient.getUser();
  if (!user || user.expired) await authClient.signinSilent();
  const fresh = await authClient.getUser();
  return fetch(path, { headers: { Authorization: `Bearer ${fresh?.access_token}` } });
}
''',
        "OIDC + PKCE + silent renew + offline_access is the modern web baseline. "
        "The API still must validate the token server-side; that part is out "
        "of scope here.",
    ),
    # ---------------- Security / Resistance ----------------
    (
        "ISO_SEC_RES_score_01_http_endpoint_in_prod",
        "ISO_SEC_RES", 1, "extreme_low", "react",
        '''export async function getOrders() {
  return fetch("http://api.acme.com/orders").then(r => r.json());
}
''',
        "Plain HTTP for production API. Traffic visible and tamperable on any "
        "shared network. Indefensible in 2026.",
    ),
    (
        "ISO_SEC_RES_score_09_audit_clean_pinning_csp",
        "ISO_SEC_RES", 9, "extreme_high", "react-native",
        '''import { fetch as pinnedFetch } from "react-native-ssl-pinning";

const PINS = ["sha256/abc...=", "sha256/def...="];   // primary + backup

export async function api(path: string, init: RequestInit = {}) {
  return pinnedFetch(`https://api.acme.com${path}`, {
    ...init,
    sslPinning: { certs: PINS, hashes: PINS },
    timeoutInterval: 8,
  });
}
''',
        "TLS + cert pinning with backup pin. Combined with npm audit clean in "
        "CI (out of band) — close to the achievable ceiling for resistance.",
    ),
    # ---------------- Security / Accountability ----------------
    (
        "ISO_SEC_ACC_score_02_no_user_context_in_logs",
        "ISO_SEC_ACC", 2, "extreme_low", "react",
        '''export async function placeOrder(items: unknown[]) {
  try {
    return await fetch("/orders", { method: "POST", body: JSON.stringify(items) });
  } catch (e) {
    console.log("order failed", e);
  }
}
''',
        "Errors logged with no userId / sessionId / orderId. Impossible to "
        "trace incidents back to specific users.",
    ),
    (
        "ISO_SEC_ACC_score_09_distributed_tracing_with_user_context",
        "ISO_SEC_ACC", 9, "extreme_high", "react",
        '''import * as Sentry from "@sentry/react";

Sentry.setUser({ id: "u_42", email: "a@b" });
Sentry.setTag("session_id", "s_19");

export async function placeOrder(items: unknown[]) {
  return Sentry.withScope(async scope => {
    scope.setContext("order", { itemCount: items.length });
    return fetch("/orders", {
      method: "POST",
      body: JSON.stringify(items),
      headers: { "x-trace-id": Sentry.getCurrentHub().getScope()?.getSpan()?.toTraceparent() ?? "" },
    });
  });
}
''',
        "User + session + trace propagated to backend; Sentry breadcrumbs "
        "enriched per-mutation. Every error is attributable.",
    ),
    # ---------------- Reliability / Faultlessness ----------------
    (
        "ISO_REL_FAULT_score_01_rules_of_hooks_violation",
        "ISO_REL_FAULT", 1, "extreme_low", "react",
        '''import { useState, useEffect } from "react";

export function Bad({ flag }: { flag: boolean }) {
  if (flag) {
    const [x, setX] = useState(0);  // conditional hook
    useEffect(() => { setX(1); });
    return <p>{x}</p>;
  }
  return null;
}
''',
        "Conditional hook breaks the render-order invariant. React will "
        "misalign hook indices across renders → crashes or wrong state.",
    ),
    (
        "ISO_REL_FAULT_score_02_any_everywhere_no_strict",
        "ISO_REL_FAULT", 2, "extreme_low", "react",
        '''export function Order({ data }: { data: any }) {
  // @ts-ignore
  const total = data.items.reduce((a, i) => a + i.price, 0);
  return <p>Total: ${total}</p>;
}
''',
        "any + @ts-ignore + property access without runtime check. Will crash "
        "the moment `data` is missing the expected shape.",
    ),
    (
        "ISO_REL_FAULT_score_09_strict_ts_with_branded_types",
        "ISO_REL_FAULT", 9, "extreme_high", "react",
        '''type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

const userId = (s: string): UserId => s as UserId;
const orderId = (s: string): OrderId => s as OrderId;

export function getOrder(uid: UserId, oid: OrderId) {
  return fetch(`/users/${uid}/orders/${oid}`);
}

const u = userId("u_42");
const o = orderId("o_19");
getOrder(u, o);          // ok
// getOrder(o, u);        // compile error — branded types prevent the swap
''',
        "Branded types make the wrong-id-order bug impossible to compile. "
        "Strict TS + parse-don't-validate is the idiomatic ceiling.",
    ),
    # ---------------- Reliability / Fault Tolerance ----------------
    (
        "ISO_REL_FT_score_01_no_error_boundary_with_network",
        "ISO_REL_FT", 1, "extreme_low", "react",
        '''import { useEffect, useState } from "react";

export function App() {
  const [data, setData] = useState<any>();
  useEffect(() => {
    fetch("/api/profile").then(r => r.json()).then(setData);
  }, []);
  return <h1>{data.name}</h1>;   // crashes on first render — no boundary
}
''',
        "No error boundary anywhere. A render-time TypeError crashes the entire "
        "app to a white screen. No recovery affordance.",
    ),
    (
        "ISO_REL_FT_score_09_layered_boundaries_with_recovery",
        "ISO_REL_FT", 9, "extreme_high", "react",
        '''import { ErrorBoundary } from "react-error-boundary";
import * as Sentry from "@sentry/react";

function Fallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <section role="alert">
      <p>This area is having trouble: {error.message}</p>
      <button onClick={resetErrorBoundary}>Try again</button>
    </section>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary FallbackComponent={Fallback}
      onError={(e, info) => Sentry.captureException(e, { extra: info })}>
      {children}
    </ErrorBoundary>
  );
}
''',
        "Boundary at component level, fallback offers recovery, error reported "
        "to monitoring with React component stack. Compose at app/route/risky-tree.",
    ),
    # ---------------- Reliability / Recoverability ----------------
    (
        "ISO_REL_REC_score_02_no_persistence_state_lost_on_refresh",
        "ISO_REL_REC", 2, "extreme_low", "react",
        '''import { useState } from "react";

export function CheckoutForm() {
  const [cart, setCart] = useState<string[]>([]);
  // refresh = empty cart, no draft, no saved progress
  return <button onClick={() => setCart([])}>Reset</button>;
}
''',
        "Multi-step form holds all state in memory. A page refresh loses the "
        "user's progress. Bad mental model on flaky connections.",
    ),
    (
        "ISO_REL_REC_score_09_persisted_with_optimistic_rollback",
        "ISO_REL_REC", 9, "extreme_high", "react",
        '''import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (next: { name: string }) =>
      fetch("/profile", { method: "PUT", body: JSON.stringify(next) }),
    onMutate: async (next) => {
      await qc.cancelQueries({ queryKey: ["profile"] });
      const prev = qc.getQueryData(["profile"]);
      qc.setQueryData(["profile"], next);
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(["profile"], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}
''',
        "Optimistic update with rollback on error. Cache invalidation on "
        "settle. Standard React Query recoverability pattern.",
    ),
    # ---------------- Performance / Time Behaviour ----------------
    (
        "ISO_PERF_TIME_score_02_inline_object_props_to_memo_child",
        "ISO_PERF_TIME", 2, "extreme_low", "react",
        '''import { memo } from "react";

const Heavy = memo(function Heavy({ config }: { config: { theme: string } }) {
  // expensive render
  return <div>{config.theme}</div>;
});

export function Parent() {
  return <Heavy config={{ theme: "dark" }} />;   // new object every render
}
''',
        "memo() defeated by inline object literal. Heavy re-renders every "
        "Parent render. Classic anti-pattern.",
    ),
    (
        "ISO_PERF_TIME_score_09_profiled_memoized_critical_paths",
        "ISO_PERF_TIME", 9, "extreme_high", "react",
        '''import { memo, useCallback, useMemo } from "react";

const Row = memo(function Row({ item, onPick }: { item: { id: string; name: string }; onPick: (id: string) => void }) {
  return <li onClick={() => onPick(item.id)}>{item.name}</li>;
});

export function List({ items }: { items: { id: string; name: string }[] }) {
  const sorted = useMemo(() => [...items].sort((a, b) => a.name.localeCompare(b.name)), [items]);
  const onPick = useCallback((id: string) => console.log("picked", id), []);
  return <ul>{sorted.map(it => <Row key={it.id} item={it} onPick={onPick} />)}</ul>;
}
''',
        "Stable callbacks via useCallback, memoized derived data, memo'd item "
        "component, stable keys. Profiler verifies zero wasted renders.",
    ),
    # ---------------- Performance / Resource Utilization ----------------
    (
        "ISO_PERF_RES_score_02_full_lodash_and_moment",
        "ISO_PERF_RES", 2, "extreme_low", "react",
        '''import _ from "lodash";        // ~70 kB
import moment from "moment";    // ~290 kB w/ locales

export function format(d: Date, items: string[]) {
  return _.uniq(items).map(i => `${moment(d).format()} - ${i}`);
}
''',
        "Full lodash + full moment for trivial usage. ~360 kB of bundle for "
        "what date-fns/dayjs + Array.from(new Set) covers in <10 kB.",
    ),
    (
        "ISO_PERF_RES_score_09_tree_shaken_and_lazy",
        "ISO_PERF_RES", 9, "extreme_high", "react",
        '''import { format } from "date-fns/format";
import { lazy, Suspense } from "react";

const Charts = lazy(() => import("./Charts"));

export function Dashboard({ d }: { d: Date }) {
  const dedup = (xs: string[]) => Array.from(new Set(xs));
  return (
    <Suspense fallback={null}>
      <p>{format(d, "yyyy-MM-dd")}</p>
      <Charts items={dedup(["a", "b", "a"])} />
    </Suspense>
  );
}
''',
        "Tree-shakeable date-fns subimport, native Set for dedup, lazy-loaded "
        "heavy module. Bundle stays tight.",
    ),
    # ---------------- Performance / Capacity ----------------
    (
        "ISO_PERF_CAP_score_01_unbounded_scrollview_with_map_rn",
        "ISO_PERF_CAP", 1, "extreme_low", "react-native",
        '''import { ScrollView, Text } from "react-native";
type Msg = { id: string; body: string };
export function Feed({ messages }: { messages: Msg[] }) {
  return <ScrollView>{messages.map(m => <Text key={m.id}>{m.body}</Text>)}</ScrollView>;
}
''',
        "ScrollView with .map renders every item, no virtualization. Drops "
        "frames at ~200 items, OOMs at thousands. Catastrophic on RN.",
    ),
    (
        "ISO_PERF_CAP_score_09_flatlist_with_geometry_hints",
        "ISO_PERF_CAP", 9, "extreme_high", "react-native",
        '''import { FlatList, Text } from "react-native";
import { memo } from "react";

const ROW_HEIGHT = 56;
type Msg = { id: string; body: string };

const Row = memo(({ item }: { item: Msg }) => <Text style={{ height: ROW_HEIGHT }}>{item.body}</Text>);

export function Feed({ messages }: { messages: Msg[] }) {
  return (
    <FlatList
      data={messages}
      keyExtractor={(i) => i.id}
      renderItem={({ item }) => <Row item={item} />}
      getItemLayout={(_, index) => ({ length: ROW_HEIGHT, offset: ROW_HEIGHT * index, index })}
      windowSize={7}
      maxToRenderPerBatch={10}
      removeClippedSubviews
    />
  );
}
''',
        "FlatList with stable keys, getItemLayout (no measurement), tuned "
        "windowSize, memoized row. Scrolls 60fps at hundreds of thousands of items.",
    ),
    # ---------------- Maintainability / Modularity ----------------
    (
        "ISO_MAINT_MOD_score_01_circular_deps_god_components",
        "ISO_MAINT_MOD", 1, "extreme_low", "react",
        '''// src/foo.ts imports from src/bar.ts; bar imports back foo.
// 800-line component handles fetching, business logic, rendering, navigation.
import { helperFromBar } from "./bar";
export function GodComponent() {
  const x = helperFromBar();
  return <div>{x}</div>;
}
''',
        "Circular dependency + god component. Hand-waved here as comments — "
        "the structural problem is what the score reflects.",
    ),
    (
        "ISO_MAINT_MOD_score_09_feature_slices_with_public_api",
        "ISO_MAINT_MOD", 9, "extreme_high", "react",
        '''// src/features/checkout/index.ts (public API)
export { CheckoutScreen } from "./screens/CheckoutScreen";
export type { CheckoutState } from "./types";
// internals (./hooks/, ./services/) are NOT re-exported.

// elsewhere:
import { CheckoutScreen, CheckoutState } from "@/features/checkout";
// importing from "@/features/checkout/services/..." is a lint error.
''',
        "Feature slice with explicit public surface; deep imports blocked by "
        "ESLint boundaries. Maximally modular within React conventions.",
    ),
    # ---------------- Maintainability / Reusability ----------------
    (
        "ISO_MAINT_REUSE_score_02_copy_pasted_card_components",
        "ISO_MAINT_REUSE", 2, "extreme_low", "react",
        '''export function ProductCard({ p }: { p: { id: string; title: string; price: number } }) {
  return <article><h2>{p.title}</h2><p>${p.price}</p></article>;
}
export function OrderCard({ o }: { o: { id: string; title: string; total: number } }) {
  return <article><h2>{o.title}</h2><p>${o.total}</p></article>;
}
export function ReviewCard({ r }: { r: { id: string; title: string; rating: number } }) {
  return <article><h2>{r.title}</h2><p>${r.rating}</p></article>;
}
''',
        "Three near-identical components diverging subtly. Bug fixes have to "
        "be repeated. No shared abstraction.",
    ),
    (
        "ISO_MAINT_REUSE_score_09_slot_pattern_card",
        "ISO_MAINT_REUSE", 9, "extreme_high", "react",
        '''import type { ReactNode } from "react";

export function Card({ title, children }: { title: ReactNode; children: ReactNode }) {
  return <article><h2>{title}</h2>{children}</article>;
}

// callers
// <Card title={p.title}><p>${p.price}</p></Card>
// <Card title={o.title}><p>${o.total}</p></Card>
''',
        "Slot pattern via children. Callers project domain-specific content. "
        "Reusable without forced configuration.",
    ),
    # ---------------- Maintainability / Analysability ----------------
    (
        "ISO_MAINT_ANAL_score_02_obscure_names_no_types_no_comments",
        "ISO_MAINT_ANAL", 2, "extreme_low", "react",
        '''export function f(a, b, c) {
  let x = [];
  for (let i = 0; i < a.length; i++) {
    if (a[i].t > b) x.push(a[i]);
  }
  return c ? x.reverse() : x;
}
''',
        "No types, opaque names, magic flags. Reader has to mentally execute "
        "to know what this does. Costly to change.",
    ),
    (
        "ISO_MAINT_ANAL_score_09_self_documenting_strict_typed",
        "ISO_MAINT_ANAL", 9, "extreme_high", "react",
        '''type Order = { id: string; placedAt: number; total: number };

export function ordersPlacedAfter(orders: ReadonlyArray<Order>, cutoff: number, newestFirst = true): Order[] {
  const filtered = orders.filter(o => o.placedAt > cutoff);
  return newestFirst ? [...filtered].sort((a, b) => b.placedAt - a.placedAt) : filtered;
}
''',
        "Strict types, expressive names, immutable inputs, intent obvious from "
        "signature. Readers do not need to read the body.",
    ),
    # ---------------- Maintainability / Modifiability ----------------
    (
        "ISO_MAINT_MOD2_score_01_state_everywhere",
        "ISO_MAINT_MOD2", 1, "extreme_low", "react",
        '''import { useState, createContext, useContext } from "react";
import { useDispatch, useSelector } from "react-redux";

const Ctx = createContext<{ user?: string }>({});

export function Profile() {
  const [user, setUser] = useState<string>("a");           // local
  const ctxUser = useContext(Ctx).user;                    // context
  const reduxUser = useSelector((s: { user: string }) => s.user); // redux
  // and somewhere a window.__user assignment...
  return <p>{user ?? ctxUser ?? reduxUser}</p>;
}
''',
        "Same concept (current user) lives in 3+ places. Any change risks "
        "drift. Modifiability collapses.",
    ),
    (
        "ISO_MAINT_MOD2_score_09_single_source_per_concern",
        "ISO_MAINT_MOD2", 9, "extreme_high", "react",
        '''import { useQuery } from "@tanstack/react-query";

export function useCurrentUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => fetch("/me").then(r => r.json()),
    staleTime: 60_000,
  });
}

// every consumer reads from useCurrentUser(); no other source of truth.
''',
        "Single source for the auth identity, owned by a query cache. Changes "
        "propagate predictably; no drift surface.",
    ),
    # ---------------- Maintainability / Testability ----------------
    (
        "ISO_MAINT_TEST_score_01_global_singletons_in_render",
        "ISO_MAINT_TEST", 1, "extreme_low", "react",
        '''import { firebaseDb } from "../firebase";   // shared singleton

export function Home() {
  const docs = (window as any).__seed__ ?? firebaseDb.collection("posts").get();
  return <ul>{(docs?.items ?? []).map((d: any) => <li>{d.title}</li>)}</ul>;
}
''',
        "Singleton imported during render + window magic for tests = nothing "
        "is mockable cleanly. Tests are flaky and brittle.",
    ),
    (
        "ISO_MAINT_TEST_score_09_di_with_msw_e2e",
        "ISO_MAINT_TEST", 9, "extreme_high", "react",
        '''type PostsApi = { listPosts(): Promise<{ id: string; title: string }[]> };

export function Home({ api }: { api: PostsApi }) {
  const [posts, setPosts] = useState<{ id: string; title: string }[]>([]);
  useEffect(() => { api.listPosts().then(setPosts); }, [api]);
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>;
}

// In tests, pass a stub `api`. In E2E (Playwright + MSW), intercept HTTP.
''',
        "Inversion of control via prop. Trivially mockable in unit tests; "
        "MSW handles E2E. Testability is a design feature, not retrofit.",
    ),
    # ---------------- Interaction Capability / Operability ----------------
    (
        "ISO_INTER_OP_score_01_div_onclick_no_role",
        "ISO_INTER_OP", 1, "extreme_low", "react",
        '''export function CloseButton({ onClose }: { onClose: () => void }) {
  return <div onClick={onClose} style={{ cursor: "pointer" }}>X</div>;
}
''',
        "<div> as a button. Not focusable, no keyboard support, no role. "
        "Inoperable without a mouse.",
    ),
    (
        "ISO_INTER_OP_score_09_focus_managed_modal",
        "ISO_INTER_OP", 9, "extreme_high", "react",
        '''import * as Dialog from "@radix-ui/react-dialog";

export function ConfirmDialog({ open, onConfirm, onClose }: { open: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content aria-labelledby="confirm-title">
          <Dialog.Title id="confirm-title">Delete this account?</Dialog.Title>
          <Dialog.Description>This cannot be undone.</Dialog.Description>
          <Dialog.Close asChild><button onClick={onConfirm}>Delete</button></Dialog.Close>
          <Dialog.Close asChild><button>Cancel</button></Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
''',
        "Radix primitives — focus trap, restore on close, ESC + click-outside, "
        "labelled, predictable keyboard. Operability ceiling for modals.",
    ),
    # ---------------- Interaction Capability / User Error Protection ----------------
    (
        "ISO_INTER_UEP_score_02_destructive_action_no_confirm",
        "ISO_INTER_UEP", 2, "extreme_low", "react",
        '''import { useMutation } from "@tanstack/react-query";

export function DeleteAllPhotosButton() {
  const m = useMutation({ mutationFn: () => fetch("/photos", { method: "DELETE" }) });
  return <button onClick={() => m.mutate()}>Delete all photos</button>;
}
''',
        "Irreversible mass-deletion fires on a single click. No confirm, no "
        "undo, no dry-run. Indefensible UX.",
    ),
    (
        "ISO_INTER_UEP_score_09_confirm_undo_with_zod",
        "ISO_INTER_UEP", 9, "extreme_high", "react",
        '''import { useState } from "react";
import { z } from "zod";

const Email = z.string().email();

export function InviteForm({ onInvite }: { onInvite: (email: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const onSubmit = async () => {
    const parsed = Email.safeParse(email);
    if (!parsed.success) { setError("Use a valid email like name@company.com"); return; }
    if (!confirm(`Invite ${parsed.data}?`)) return;
    await onInvite(parsed.data);
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <label>Email <input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      {error && <p role="alert">{error}</p>}
      <button>Send invite</button>
    </form>
  );
}
''',
        "Zod-validated email, actionable error message, explicit confirm, "
        "predictable form behavior. Errors are recoverable with one step.",
    ),
    # ---------------- Interaction Capability / Inclusivity ----------------
    (
        "ISO_INTER_INC_score_01_form_no_labels_low_contrast",
        "ISO_INTER_INC", 1, "extreme_low", "react",
        '''export function Login() {
  return (
    <form style={{ background: "#888", color: "#999" }}>
      <input placeholder="email" />
      <input placeholder="password" type="password" />
      <button>Go</button>
    </form>
  );
}
''',
        "Inputs without labels, contrast ratio ~1.1:1 (WCAG fails AA at 4.5). "
        "Unusable for screen-reader and low-vision users.",
    ),
    (
        "ISO_INTER_INC_score_09_full_a11y_with_i18n",
        "ISO_INTER_INC", 9, "extreme_high", "react",
        '''import { useTranslation } from "react-i18next";

export function Login({ onSubmit }: { onSubmit: (email: string, pw: string) => void }) {
  const { t } = useTranslation();
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(emailRef.current!.value, pwRef.current!.value); }}
          aria-labelledby="login-title">
      <h1 id="login-title">{t("login.title")}</h1>
      <label htmlFor="email">{t("login.email")}</label>
      <input id="email" type="email" required ref={emailRef} autoComplete="email" />
      <label htmlFor="pw">{t("login.password")}</label>
      <input id="pw" type="password" required ref={pwRef} autoComplete="current-password" />
      <button>{t("login.submit")}</button>
    </form>
  );
}
declare const emailRef: React.RefObject<HTMLInputElement>;
declare const pwRef: React.RefObject<HTMLInputElement>;
''',
        "Labelled inputs, i18n-ready strings, autoComplete hints, semantic "
        "form. Tested with VoiceOver/NVDA — narration is correct.",
    ),
    # ---------------- Compatibility ----------------
    (
        "ISO_COMP_COEX_score_02_peer_dep_warnings_ignored",
        "ISO_COMP_COEX", 2, "extreme_low", "react",
        '''// package.json:
// {
//   "dependencies": { "react": "16.4.0", "react-router-dom": "^6.20.0" }
// }
// — react-router-dom@6 requires react ^17. Install logs warnings; team
//    ignores them; React 16 ships to prod.
export {};
''',
        "Peer-dep warnings ignored. The runtime is in an unsupported state — "
        "any subtle bug becomes 'works on my machine' permanently.",
    ),
    (
        "ISO_COMP_COEX_score_09_engines_pinned_ci_matrix",
        "ISO_COMP_COEX", 9, "extreme_high", "react",
        '''// package.json:
// "engines": { "node": ">=18.18 <21" },
// "devDependencies": { "react": "18.3.1", "react-router-dom": "6.27.0" }
// CI runs on node 18, 20; tests pass on iOS 16/17, Android 12/13/14.
export {};
''',
        "Engines pinned, peer deps consistent, multi-version CI matrix. The "
        "co-existence envelope is explicit and verified.",
    ),
    (
        "ISO_COMP_INTER_score_02_handwritten_drifting_api_types",
        "ISO_COMP_INTER", 2, "extreme_low", "react",
        '''type User = { id: string; name: string; email: string };
// Backend renamed `name` to `displayName` last sprint.
// This file still has `name`. Runtime returns undefined silently.
export async function loadMe(): Promise<User> {
  return fetch("/me").then(r => r.json());
}
''',
        "Handwritten types diverged from the API. Runtime returns undefined "
        "for fields that should exist. Interop is illusory.",
    ),
    (
        "ISO_COMP_INTER_score_09_codegen_plus_runtime_validation",
        "ISO_COMP_INTER", 9, "extreme_high", "react",
        '''// types/api.ts is generated by openapi-typescript on every build.
// Wrap with Zod for runtime validation.
import type { paths } from "./types/api";
import { z } from "zod";

const MeResponse = z.object({ id: z.string(), displayName: z.string(), email: z.string().email() });
export type Me = z.infer<typeof MeResponse>;

export async function loadMe(): Promise<Me> {
  return MeResponse.parse(await fetch("/me").then(r => r.json()));
}
''',
        "OpenAPI-driven types + Zod at the boundary. Backend changes break "
        "the build; runtime validation catches drifts in older deploys.",
    ),
    # ---------------- Flexibility ----------------
    (
        "ISO_FLEX_ADAPT_score_02_fixed_widths_no_dark_mode",
        "ISO_FLEX_ADAPT", 2, "extreme_low", "react",
        '''export function Card() {
  return <article style={{ width: 800, color: "#000", background: "#fff" }} />;
}
''',
        "Fixed pixel width, hardcoded colors, no theme. Breaks on phones, "
        "ignores dark mode preferences. Inflexible.",
    ),
    (
        "ISO_FLEX_ADAPT_score_09_token_driven_responsive_dark_mode",
        "ISO_FLEX_ADAPT", 9, "extreme_high", "react",
        '''import { useColorScheme } from "react-native";

const tokens = {
  light: { surface: "#fff", text: "#0b0b0b" },
  dark:  { surface: "#0b0b0b", text: "#f5f5f5" },
};

export function Card({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme();
  const t = tokens[scheme === "dark" ? "dark" : "light"];
  return <article style={{ padding: 16, color: t.text, background: t.surface }}>{children}</article>;
}
''',
        "Theme tokens drive color, fluid sizing, OS preference respected. "
        "Adapts cleanly to dark/light, mobile/tablet.",
    ),
    (
        "ISO_FLEX_SCAL_score_01_no_split_no_virtual",
        "ISO_FLEX_SCAL", 1, "extreme_low", "react",
        '''import HeavyEditor from "./HeavyEditor"; // 1.2 MB

export function App({ items }: { items: string[] }) {
  return (
    <>
      <HeavyEditor />
      <ul>{items.map(i => <li key={i}>{i}</li>)}</ul>
    </>
  );
}
''',
        "Heavy editor in the initial bundle even on routes that do not need "
        "it. List unbounded with .map. Will not scale to large data or "
        "moderate bundle budgets.",
    ),
    (
        "ISO_FLEX_SCAL_score_09_lazy_routes_virtualized_lists",
        "ISO_FLEX_SCAL", 9, "extreme_high", "react",
        '''import { lazy, Suspense } from "react";
import { FixedSizeList } from "react-window";

const HeavyEditor = lazy(() => import("./HeavyEditor"));

export function App({ items }: { items: string[] }) {
  return (
    <>
      <Suspense fallback={null}><HeavyEditor /></Suspense>
      <FixedSizeList itemCount={items.length} itemSize={32} height={400} width={"100%"}>
        {({ index, style }) => <div style={style}>{items[index]}</div>}
      </FixedSizeList>
    </>
  );
}
''',
        "Lazy split + virtualized list. Bundle and DOM both scale sub-linearly "
        "with payload size.",
    ),
    (
        "ISO_FLEX_REPL_score_02_firebase_imported_in_components",
        "ISO_FLEX_REPL", 2, "extreme_low", "react",
        '''import { firestore } from "firebase/firestore";

export function Home() {
  // Component talks to Firebase directly. Migrating off Firebase later
  // touches every component.
  return <div>{firestore?.toString()}</div>;
}
''',
        "Vendor SDK imported into UI components. Replacing the backend "
        "requires editing every consumer.",
    ),
    (
        "ISO_FLEX_REPL_score_09_data_layer_behind_hooks",
        "ISO_FLEX_REPL", 9, "extreme_high", "react",
        '''// data/index.ts — single seam over the storage backend.
export interface PostsRepo { list(): Promise<{ id: string; title: string }[]> }

// data/firebase.ts (impl)
// data/postgrest.ts (alt impl)
// data/mock.ts (test impl)

// hook
import { useQuery } from "@tanstack/react-query";
import { repo } from "./data";   // chosen at app bootstrap

export function usePosts() {
  return useQuery({ queryKey: ["posts"], queryFn: () => repo.list() });
}
''',
        "All UI components talk to a hook. The data layer is an interface "
        "with multiple implementations. Replacing the backend is a single "
        "edit at the bootstrap site.",
    ),
    # ---------------- Safety ----------------
    (
        "ISO_SAFE_FS_score_01_destructive_failure_unrolled",
        "ISO_SAFE_FS", 1, "extreme_low", "react",
        '''export async function transfer(amount: number) {
  await fetch("/balance/debit", { method: "POST", body: JSON.stringify({ amount }) });
  await fetch("/balance/credit", { method: "POST", body: JSON.stringify({ amount }) });
  // Any error between these two leaves money debited but not credited.
}
''',
        "Two-step money move with no rollback, no idempotency, no compensating "
        "transaction. Unsafe failure mode by construction.",
    ),
    (
        "ISO_SAFE_FS_score_09_idempotent_with_compensation",
        "ISO_SAFE_FS", 9, "extreme_high", "react",
        '''import { v4 as uuid } from "uuid";

export async function transfer(amount: number) {
  const txId = uuid();
  const res = await fetch("/transfers", {
    method: "POST",
    headers: { "Idempotency-Key": txId, "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) throw new Error("transfer failed; backend will compensate via tx id " + txId);
  return await res.json();
}
''',
        "Single atomic backend call with idempotency key. Caller can retry "
        "safely; backend owns compensation. Fail-safe by design.",
    ),
    (
        "ISO_SAFE_SI_score_02_unaudited_native_modules",
        "ISO_SAFE_SI", 2, "extreme_low", "react-native",
        '''// package.json includes "react-native-some-random-cool-thing"
// (123 stars, 1 maintainer, last commit 2 years ago, unmaintained).
// Used in production. No security review.
export {};
''',
        "Unaudited, unmaintained native module in dependency chain. Each "
        "release opens a supply-chain hole.",
    ),
    (
        "ISO_SAFE_SI_score_09_sbom_provenance_audit",
        "ISO_SAFE_SI", 9, "extreme_high", "react-native",
        '''// CI runs:
// - npm audit --audit-level=moderate (blocks merges on advisories)
// - syft generates SBOM, uploaded as build artifact
// - cosign verifies signed releases of native modules
// - WebView restricted to https://my.app, JS bridge audited per release
export {};
''',
        "SBOM + provenance + audit gating + WebView hardening. Integration "
        "surface is small, audited, and signed.",
    ),
    # ---------------- Functional Suitability / Correctness ----------------
    (
        "ISO_FUN_CORR_score_01_no_e2e_no_unit_history_of_regressions",
        "ISO_FUN_CORR", 1, "extreme_low", "react",
        '''// Codebase has zero tests. Bug tracker shows 14 reopened
// "fixed regression" tickets in the last 6 months.
export {};
''',
        "No tests, repeated regressions on previously-fixed bugs. Functional "
        "correctness is unmeasured and demonstrably weak.",
    ),
    (
        "ISO_FUN_CORR_score_09_e2e_critical_paths_mutation_tested",
        "ISO_FUN_CORR", 9, "extreme_high", "react",
        '''// Critical user flows covered by Playwright E2E (auth, checkout,
// data mutations). Stryker mutation testing shows ~85% mutation kill
// on core lib. Each closed bug has a regression test attached.
export {};
''',
        "Critical paths E2E + mutation testing on core lib. Bug regressions "
        "detected automatically. Functional correctness measurably high.",
    ),
    # ---------------- Extra anchors (bring total above 60) ----------------
    (
        "ISO_INTER_UAA_score_02_errors_without_recovery",
        "ISO_INTER_UAA", 2, "extreme_low", "react",
        '''export function ResetPassword({ error }: { error: string | null }) {
  if (error) return <p>Error: {error}</p>;   // raw, no next step
  return null;
}
''',
        "Raw error string surfaced to the user, no retry / contact / fallback. "
        "User assistance reaches the user but offers nothing actionable.",
    ),
    (
        "ISO_INTER_UAA_score_09_actionable_errors_with_handoff",
        "ISO_INTER_UAA", 9, "extreme_high", "react",
        '''type ApiError = { code: "rate_limited" | "invalid_email" | "server"; message: string; ref?: string };

export function ResetPasswordError({ err, onRetry }: { err: ApiError; onRetry: () => void }) {
  if (err.code === "rate_limited") return <p>Too many tries. Wait 5 minutes, then <button onClick={onRetry}>retry</button>.</p>;
  if (err.code === "invalid_email") return <p>That email is not registered. <a href="/signup">Create an account</a>.</p>;
  return <p>Something went wrong (ref {err.ref}). <a href="/support">Contact support</a>.</p>;
}
''',
        "Error states are typed, copy is specific and actionable, support "
        "handoff includes a reference. User assistance is real.",
    ),
    (
        "ISO_INTER_SD_score_02_no_async_states",
        "ISO_INTER_SD", 2, "extreme_low", "react",
        '''import { useEffect, useState } from "react";
export function Inbox() {
  const [msgs, setMsgs] = useState<string[]>([]);
  useEffect(() => { fetch("/inbox").then(r => r.json()).then(setMsgs); }, []);
  return <ul>{msgs.map(m => <li key={m}>{m}</li>)}</ul>;
  // No loading, no empty state, no error state. UI shows blank during fetch.
}
''',
        "No loading / empty / error states. The UI is silent while fetching "
        "and on failure. Self-descriptiveness collapses.",
    ),
]


def main() -> None:
    for slug, sub_id, score, tier, framework, code, justification in ANCHORS:
        d = ROOT / slug
        d.mkdir(parents=True, exist_ok=True)
        ext = "tsx" if "<" in code or "/>" in code else "ts"
        (d / f"code.{ext}").write_text(code)
        (d / "manifest.json").write_text(json.dumps({
            "iso_sub_id": sub_id,
            "expected_score_1_to_10": score,
            "tier": tier,
            "framework": framework,
            "size_loc": code.count("\n"),
            "justification": justification,
        }, indent=2) + "\n")
    print(f"Wrote {len(ANCHORS)} anchors to {ROOT}")


if __name__ == "__main__":
    main()

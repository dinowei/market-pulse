// The Node static-render harness has no Next App Router context. Browser behavior
// is covered by Playwright; this narrow test double only supplies the router shape
// needed to render client components without fabricating route state.
export function useRouter() {
  return { push() {} };
}

// A static render has no query string: an empty URLSearchParams, never invented params.
export function useSearchParams() {
  return new URLSearchParams();
}

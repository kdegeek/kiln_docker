import { browser } from "$app/environment"
import { dev } from "$app/environment"

export const prerender = true
export const ssr = false

export const load = async () => {
  // Analytics disabled - PostHog removed to avoid CSP issues
  return
}

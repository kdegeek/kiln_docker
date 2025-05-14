import type { Writable } from "svelte/store"
import { localStorageStore } from "../stores"

export type ProgressUIState = {
  progress: number | null
  title: string
  body: string
  cta: string | null
  link: string
}

export const progress_ui_state: Writable<ProgressUIState | null> =
  localStorageStore("progress_ui_state", null)

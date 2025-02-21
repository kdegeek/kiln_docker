import type { EvalOutputScore, EvalTemplate } from "$lib/types"

export type EvalTemplateResult = {
  // Server IDs are EvalTemplate. We have a custom "none" value for the UI.
  template_id: EvalTemplate | "none"
  name: string
  description: string
  output_scores: EvalOutputScore[]
}

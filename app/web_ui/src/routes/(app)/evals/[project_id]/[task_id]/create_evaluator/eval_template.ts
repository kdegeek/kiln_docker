import type { EvalOutputScore } from "$lib/types"

export type EvalTemplateResult = {
  template_id: string
  name: string
  description: string
  output_scores: EvalOutputScore[]
}

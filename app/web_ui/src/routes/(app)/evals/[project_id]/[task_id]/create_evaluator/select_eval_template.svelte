<script lang="ts">
  import type { EvalTemplateResult } from "./eval_template"
  import type { Task } from "$lib/types"
  export let selected_template_callback: (template: EvalTemplateResult) => void
  export let task: Task | null | undefined

  interface EvaluatorTemplateDescription {
    id: string
    name: string
    description: string
    recommended?: boolean
    eval_template?: EvalTemplateResult | undefined
  }

  const evaluator_template_descriptions: EvaluatorTemplateDescription[] = [
    {
      id: "kiln_requirements",
      name: "Task Requirements and Overall Scores",
      description:
        "Use the requirements you setup as part of your task to evaluate quality. We'll generate scores for each task requirement, and one for 'Overall Rating'. You can easily compare the evaluator to existing human ratings from Kiln UI.",
      recommended: true,
    },
    {
      id: "toxicity",
      name: "Toxicity Evaluator",
      description: "Evaluate the toxicity of the model's output.",
      eval_template: {
        template_id: "toxicity",
        name: "Toxicity Evaluator",
        description: "Evaluate the toxicity of the model's output.",
        output_scores: [
          {
            name: "Toxicity",
            type: "pass_fail",
            instruction: "Evaluate the toxicity of the model's output.",
          },
        ],
      },
    },
    {
      id: "Custom Goal",
      name: "Custom Goal and Scores",
      description:
        "Write an evaluator from scratch. You'll be able to specify a goal and write instructions to evaluate quality.",
      eval_template: {
        template_id: "custom",
        name: "",
        description: "",
        // Blank to create a line item in UI
        output_scores: [
          {
            name: "",
            type: "five_star",
            instruction: "",
          },
        ],
      },
    },
  ]

  function select_template(
    template_id: string,
    template: EvalTemplateResult | undefined,
  ) {
    // No op
    if (!selected_template_callback) {
      return
    }

    // Static templates are easy
    if (template) {
      selected_template_callback(template)
      return
    }

    if (template_id === "kiln_requirements") {
      if (!task) {
        alert("Task is required for this template, and task failed to load.")
        return
      }

      const output_scores = task.requirements.map((requirement) => ({
        name: requirement.name,
        type: requirement.type,
        instruction: requirement.instruction,
      }))
      output_scores.push({
        name: "Overall Rating",
        type: "five_star",
        instruction: "Evaluate the overall quality of the output.",
      })

      selected_template_callback({
        template_id: "kiln_requirements",
        name: "Overall Score and Task Requirements",
        description:
          "Evaluates each of the task requirements and the 'Overall Rating'.",
        output_scores: output_scores,
      })
      return
    }

    alert(`Template ID ${template_id} not found`)
  }
</script>

<div class="flex flex-col gap-4 pt-12 max-w-[500px] mx-auto">
  <div class="text-xl font-bold pb-10 text-center">
    Select Evaluator Template
  </div>
  {#each evaluator_template_descriptions as template_description}
    <button
      class="cursor-pointer text-left"
      on:click={() => {
        select_template(
          template_description.id,
          template_description.eval_template,
        )
      }}
    >
      <div
        class="card card-bordered border-base-300 bg-base-200 shadow-md w-full p-6 indicator"
      >
        {#if template_description.recommended}
          <div class="indicator-item indicator-center badge badge-primary">
            Recommended
          </div>
        {/if}
        <div class="flex flex-col gap-2">
          <div class="font-medium">
            {template_description.name}
          </div>
          <div class="font-light">
            {template_description.description}
          </div>
        </div>
      </div>
    </button>
  {/each}
</div>

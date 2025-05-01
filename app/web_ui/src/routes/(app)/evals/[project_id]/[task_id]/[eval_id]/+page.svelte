<script lang="ts">
  import AppPage from "../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import type { EvalProgress } from "$lib/types"
  import InfoTooltip from "$lib/ui/info_tooltip.svelte"

  import Warning from "$lib/ui/warning.svelte"
  import EditDialog from "$lib/ui/edit_dialog.svelte"

  $: project_id = $page.params.project_id
  $: task_id = $page.params.task_id
  $: eval_id = $page.params.eval_id

  let evaluator: Eval | null = null
  let eval_error: KilnError | null = null
  let eval_loading = true

  let eval_progress_loading = true
  let eval_progress: EvalProgress | null = null
  let eval_progress_error: KilnError | null = null

  $: loading = eval_loading || eval_progress_loading
  $: error = eval_error || eval_progress_error

  onMount(async () => {
    // Wait for page params to load
    await tick()
    // Load data in parallel
    await Promise.all([get_eval(), get_eval_progress()])
  })

  async function get_eval() {
    try {
      eval_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}",
        {
          params: {
            path: {
              project_id,
              task_id,
              eval_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      evaluator = data
    } catch (error) {
      eval_error = createKilnError(error)
    } finally {
      eval_loading = false
    }
  }

  async function get_eval_progress() {
    eval_progress = null
    eval_progress_loading = true
    try {
      eval_progress = null
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/progress",
        {
          params: {
            path: {
              project_id,
              task_id,
              eval_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      eval_progress = data
    } catch (error) {
      eval_progress_error = createKilnError(error)
    } finally {
      eval_progress_loading = false
    }
  }

  type UiProperty = {
    name: string
    value: string
    tooltip?: string
    link?: string
  }

  function get_eval_properties(
    evaluator: Eval,
    eval_progress: EvalProgress | null,
  ): UiProperty[] {
    const properties: UiProperty[] = []

    properties.push({
      name: "Name",
      value: evaluator.name,
    })
    if (evaluator.description) {
      properties.push({
        name: "Description",
        value: evaluator.description,
      })
    }
    properties.push({
      name: "ID",
      value: evaluator.id || "unknown",
    })

    let eval_set_size = ""
    if (eval_progress) {
      eval_set_size = " (" + eval_progress.dataset_size + " items)"
    }
    properties.push({
      name: "Eval Dataset",
      value: evaluator.eval_set_filter_id + eval_set_size,
      link: link_from_filter_id(evaluator.eval_set_filter_id),
    })
    let golden_dataset_size = ""
    if (eval_progress) {
      golden_dataset_size = " (" + eval_progress.golden_dataset_size + " items)"
    }
    properties.push({
      name: "Golden Dataset",
      value: evaluator.eval_configs_filter_id + golden_dataset_size,
      tooltip:
        "This is the dataset that we use to evaluate the quality of the evaluation method. Also called the 'Eval Method Dataset'. It needs to have human ratings.",
      link: link_from_filter_id(evaluator.eval_configs_filter_id),
    })
    return properties
  }

  $: has_default_eval_config = evaluator && evaluator.current_config_id

  let edit_dialog: EditDialog | null = null

  const MIN_DATASET_SIZE = 25
  let current_step: 0 | 1 | 2 | 3 | 4 | 5 | 6 = 0
  let required_more_eval_data = false
  let required_more_golden_data = false
  let goals: string[] = []
  const step_titles: string[] = [
    "Define Goals",
    "Create Eval Data",
    "Human Ratings",
    "Find the Best Evaluator",
    "Find the Best Way to Run this Task",
  ]
  const step_tooltips: Record<number, string> = {
    1: "Each eval needs a set of quality goals to measure (aka 'eval scores'). You can add separate evals for different goals, or multiple goals to the same eval.",
    2: "Each eval needs two datasets: one for ensuring the eval works, and another to help find the best way of running your task. We'll help you create both with synthetic data!",
    3: "Rating your 'golden' dataset lets us determine if the evaluator is working well by checking if it aligns to human preferences.",
    4: "Benchmark different evaluation methods (models, prompts, algorithms). We'll compare to your golden dataset to find the evaluator which best matches human preferences.",
    5: "Which model, prompt, or fine-tune is is the highest quality for this task? This tool will help your compare different options and find the best one.",
  }
  function update_eval_progress(
    progress: EvalProgress | null,
    evaluator: Eval | null,
  ) {
    current_step = 1
    if (!progress || !evaluator) {
      return
    }

    // Goals are setup. Generate friendly names for them.
    goals = []
    for (const output of evaluator.output_scores) {
      goals.push(output.name + " (" + output.type + ")")
    }

    current_step = 2
    required_more_eval_data = progress.dataset_size < MIN_DATASET_SIZE
    required_more_golden_data = progress.golden_dataset_size < MIN_DATASET_SIZE
    if (required_more_eval_data || required_more_golden_data) {
      return
    }
    current_step = 3
    // TODO: exist if step 3

    current_step = 4
    if (!has_default_eval_config) {
      return
    }

    current_step = 5
    // TODO: exist if step 5

    current_step = 6
  }
  $: update_eval_progress(eval_progress, evaluator)

  function link_from_filter_id(filter_id: string): string | undefined {
    if (filter_id.startsWith("tag::")) {
      return `/dataset/${project_id}/${task_id}?tags=${filter_id.replace("tag::", "")}`
    }
    return undefined
  }
</script>

<div class="max-w-[1400px]">
  <AppPage
    title="Eval: {evaluator?.name || ''}"
    subtitle="Evals help you measure quality"
    sub_subtitle="Learn About Evals"
    sub_subtitle_link="https://docs.getkiln.ai/docs/evaluations"
    action_buttons={[
      {
        label: "Edit",
        handler: () => {
          edit_dialog?.show()
        },
      },
    ]}
  >
    {#if loading}
      <div class="w-full min-h-[50vh] flex justify-center items-center">
        <div class="loading loading-spinner loading-lg"></div>
      </div>
    {:else if error}
      <div
        class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
      >
        <div class="font-medium">Error Loading Evaluator</div>
        <div class="text-error text-sm">
          {error.getMessage() || "An unknown error occurred"}
        </div>
      </div>
    {:else if evaluator}
      <div class="flex flex-col xl:flex-row gap-8 xl:gap-16 mb-8">
        <div class="grow">
          <ul class="steps steps-vertical ml-4 w-full">
            {#each [1, 2, 3, 4, 5] as step}
              <li
                class="step {current_step >= step ? 'step-primary' : ''}"
                data-content={current_step == step
                  ? "●"
                  : current_step > step
                    ? "✓"
                    : ""}
              >
                <div class="text-left py-4">
                  <div class="font-medium">
                    {step_titles[step - 1]}
                    {#if step_tooltips[step]}
                      <InfoTooltip
                        tooltip_text={step_tooltips[step]}
                        right={true}
                      />
                    {/if}
                  </div>
                  <div class="text-sm text-gray-500">
                    {#if step == 1 && goals.length > 0}
                      This eval has {goals.length} goals: {goals.join(", ")}.
                    {:else if step == 2}
                      <div>
                        <button
                          class="btn mt-2 {current_step == 2
                            ? 'btn-primary'
                            : 'btn-sm'}"
                        >
                          Add Eval Data
                        </button>
                        {#if eval_progress && eval_progress.dataset_size > 0 && required_more_eval_data}
                          <div class="mt-4">
                            <Warning
                              warning_message={`There are only ${eval_progress.dataset_size} items in your eval dataset. This is generally too small to get a good sense of how well your task run methods perform. We recommend at least ${MIN_DATASET_SIZE} items.`}
                              warning_color="warning"
                              tight={true}
                            />
                          </div>
                        {/if}
                        {#if eval_progress && eval_progress.golden_dataset_size > 0 && required_more_golden_data}
                          <div class="mt-4">
                            <Warning
                              warning_message={`There are only ${eval_progress.golden_dataset_size} items in your golden dataset. This is generally too small to get a good sense of how well your eval method performs. We recommend at least ${MIN_DATASET_SIZE} items.`}
                              warning_color="warning"
                              tight={true}
                            />
                          </div>
                        {/if}
                      </div>
                    {:else if step == 3}
                      <div>
                        {#if link_from_filter_id(evaluator.eval_configs_filter_id)}
                          <a
                            class="btn mt-2 {current_step == 4
                              ? 'btn-primary'
                              : 'btn-sm'}"
                            href={link_from_filter_id(
                              evaluator.eval_configs_filter_id,
                            )}
                          >
                            Rate Golden Dataset
                          </a>
                        {:else}
                          <!-- We always use "tag::" so this shouldn't happen unless it's created by code. -->
                          Your golden dataset is filtered by
                          <span class="font-mono bg-gray-100 p-1"
                            >{evaluator.eval_configs_filter_id}</span
                          >. Please rate these entries in the
                          <a
                            class="link"
                            href={`/dataset/${project_id}/${task_id}`}
                            >dataset tab</a
                          >.
                        {/if}
                      </div>
                    {:else if step == 4}
                      <div>
                        <a
                          class="btn mt-2 {current_step == 4
                            ? 'btn-primary'
                            : 'btn-sm'}"
                          href={`/evals/${project_id}/${task_id}/${eval_id}/eval_configs`}
                        >
                          Compare Eval Methods
                        </a>
                      </div>
                    {:else if step == 5}
                      <div>
                        <a
                          class="btn mt-2 {current_step == 5
                            ? 'btn-primary'
                            : 'btn-sm'}"
                          href={`/evals/${project_id}/${task_id}/${eval_id}/compare_run_methods`}
                        >
                          Compare Run Methods
                        </a>
                      </div>
                    {/if}
                  </div>
                </div>
              </li>
            {/each}
          </ul>
        </div>

        <div class="w-72 2xl:w-96 flex-none">
          <div class="text-xl font-bold mb-4">Evaluator Properties</div>
          <div
            class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
          >
            {#each get_eval_properties(evaluator, eval_progress) as property}
              <div class="flex items-center">
                {property.name}
                {#if property.tooltip}
                  <InfoTooltip tooltip_text={property.tooltip} />
                {/if}
              </div>
              <div class="flex items-center text-gray-500 overflow-x-hidden">
                {#if property.link}
                  <a href={property.link} class="link">{property.value}</a>
                {:else}
                  {property.value}
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </AppPage>
</div>

<EditDialog
  bind:this={edit_dialog}
  name="Eval"
  patch_url={`/api/projects/${project_id}/tasks/${task_id}/eval/${eval_id}`}
  delete_url={`/api/projects/${project_id}/tasks/${task_id}/eval/${eval_id}`}
  fields={[
    {
      label: "Eval Name",
      description: "A name to identify this eval.",
      api_name: "name",
      value: evaluator?.name || "",
      input_type: "input",
    },
    {
      label: "Description",
      description: "A description of the eval for you and your team.",
      api_name: "description",
      value: evaluator?.description || "",
      input_type: "textarea",
      optional: true,
    },
  ]}
/>

<script lang="ts">
  import AppPage from "../../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client, base_url } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import RunEval from "./../run_eval.svelte"
  import type { EvalConfig, EvalConfigCompareSummary } from "$lib/types"
  import FormElement from "$lib/utils/form_element.svelte"
  import {
    model_info,
    load_model_info,
    model_name,
    provider_name_from_id,
    load_available_prompts,
    load_available_models,
  } from "$lib/stores"
  import Warning from "$lib/ui/warning.svelte"
  import InfoTooltip from "$lib/ui/info_tooltip.svelte"
  import { string_to_json_key } from "$lib/utils/json_schema_editor/json_schema_templates"
  import EvalConfigInstruction from "./eval_config_instruction.svelte"
  import Dialog from "$lib/ui/dialog.svelte"
  import { eval_config_to_ui_name } from "$lib/utils/formatters"
  import type { TaskOutputRatingType } from "$lib/types"

  let score_legend_dialog: Dialog | null = null

  let evaluator: Eval | null = null
  let eval_error: KilnError | null = null
  let eval_loading = true

  let eval_config_instructions_dialog: Dialog | null = null
  let displayed_eval_config: EvalConfig | null = null

  let eval_configs: EvalConfig[] | null = null
  let eval_configs_error: KilnError | null = null
  let eval_configs_loading = true

  let score_summary: EvalConfigCompareSummary | null = null
  let score_summary_error: KilnError | null = null
  let score_summary_loading = false

  let score_type: "mse" | "mae" | "norm_mse" | "norm_mae" = "norm_mse"

  $: loading = eval_loading || eval_configs_loading || score_summary_loading
  $: error = eval_error || eval_configs_error || score_summary_error
  $: run_eval_url = `${base_url}/api/projects/${$page.params.project_id}/tasks/${$page.params.task_id}/eval/${$page.params.eval_id}/run_eval_config_eval`

  onMount(async () => {
    // Wait for page params to load
    await tick()
    // Wait for these 3 to load, as they are needed for better labels. Usually already cached and instant.
    await Promise.all([
      load_model_info(),
      load_available_prompts(),
      load_available_models(),
      // Get this first, as we want to know "current" for sorting
      get_eval(),
    ])
    // These can be parallel
    get_eval_config()
    get_score_summary()
  })

  async function get_eval() {
    try {
      eval_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}",
        {
          params: {
            path: {
              project_id: $page.params.project_id,
              task_id: $page.params.task_id,
              eval_id: $page.params.eval_id,
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

  async function get_eval_config() {
    try {
      eval_configs_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_configs",
        {
          params: {
            path: {
              project_id: $page.params.project_id,
              task_id: $page.params.task_id,
              eval_id: $page.params.eval_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      // sort with current on top
      eval_configs = data.sort((a, b) => {
        if (evaluator && a.id === evaluator.current_config_id) return -1
        if (evaluator && b.id === evaluator.current_config_id) return 1
        return 0
      })
    } catch (error) {
      eval_configs_error = createKilnError(error)
    } finally {
      eval_configs_loading = false
    }
  }

  async function get_score_summary() {
    score_summary = null
    try {
      score_summary_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_configs_score_summary",
        {
          params: {
            path: {
              project_id: $page.params.project_id,
              task_id: $page.params.task_id,
              eval_id: $page.params.eval_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      score_summary = data
    } catch (error) {
      score_summary_error = createKilnError(error)
    } finally {
      score_summary_loading = false
    }
  }

  type UiProperty = {
    name: string
    value: string
  }

  function get_eval_properties(
    evaluator: Eval,
    score_summary: EvalConfigCompareSummary | null,
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

    let eval_configs_set_size = ""
    if (score_summary) {
      eval_configs_set_size = " (" + score_summary.dataset_size + " items)"
    }
    properties.push({
      name: "Eval Method Dataset",
      value: evaluator.eval_configs_filter_id + eval_configs_set_size,
    })
    return properties
  }

  function incomplete_warning(
    score_summary: EvalConfigCompareSummary | null,
  ): string[] {
    if (!score_summary) {
      return []
    }

    const warnings: string[] = []
    if (score_summary.dataset_size === 0) {
      warnings.push(
        "There are zero items in your eval method dataset. Generate some runs in your dataset tab, and tag them to add them to your eval method dataset.",
      )
    }
    if (score_summary.not_rated_count > 0) {
      warnings.push(
        `${score_summary.not_rated_count} item(s) in your eval method dataset are not rated at all. Add human ratings to these items in the dataset tab.`,
      )
    }
    if (score_summary.partially_rated_count > 0) {
      warnings.push(
        `${score_summary.partially_rated_count} item(s) in your eval method dataset are only partially rated. Add human ratings for each score in the dataset tab.`,
      )
    }

    const completion_values = Object.values(
      score_summary.eval_config_percent_complete,
    )
    const minComplete =
      completion_values.length > 0
        ? completion_values.reduce((min, val) => Math.min(min, val), 1.0)
        : 1.0
    if (minComplete < 1.0) {
      warnings.push(
        "You evals are incomplete. Click 'Run Evals' to generate scores for the missing items.",
      )
    }

    return warnings
  }

  async function set_current_eval_config(
    eval_config_id: string | null | undefined,
  ) {
    if (!eval_config_id) {
      return
    }
    try {
      const { data, error } = await client.POST(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/set_current_eval_config/{eval_config_id}",
        {
          params: {
            path: {
              project_id: $page.params.project_id,
              task_id: $page.params.task_id,
              eval_id: $page.params.eval_id,
              eval_config_id: eval_config_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      // Update the evaluator with the latest
      evaluator = data
    } catch (error) {
      eval_error = createKilnError(error)
    }
  }

  function info_tooltip_text(
    rating_type: TaskOutputRatingType,
    score_type: "mse" | "mae" | "norm_mse" | "norm_mae",
  ) {
    let label = ""
    if (score_type === "mae") {
      label = "Mean absolute error"
    } else if (score_type === "mse") {
      label = "Mean squared error"
    } else if (score_type === "norm_mse") {
      label = "Normalized mean squared error"
    } else if (score_type === "norm_mae") {
      label = "Normalized mean absolute error"
    }
    label += " for "
    if (rating_type === "five_star") {
      label += "1 to 5 star rating."
    } else if (rating_type === "pass_fail") {
      label += "pass/fail rating."
    } else if (rating_type === "pass_fail_critical") {
      label += "pass/fail/critical rating."
    }
    return label
  }
</script>

<AppPage
  title="Compare Evaluation Methods"
  subtitle="Find the evaluation method that best matches human-ratings"
  action_buttons={[
    {
      label: "Add Eval Method",
      href: `/evals/${$page.params.project_id}/${$page.params.task_id}/${$page.params.eval_id}/create_eval_config?next_page=eval_configs`,
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
      <div class="font-medium">Error Loading</div>
      <div class="text-error text-sm">
        {error.getMessage() || "An unknown error occurred"}
      </div>
    </div>
  {:else if evaluator}
    <div class="flex flex-col xl:flex-row gap-8 xl:gap-16 mb-8">
      <div class="grow">
        <div class="text-xl font-bold mb-4">Evaluator Properties</div>
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each get_eval_properties(evaluator, score_summary) as property}
            <div class="flex items-center">{property.name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {property.value}
            </div>
          {/each}
        </div>
        {#if score_summary && score_summary.dataset_size > 0 && score_summary.dataset_size < 25}
          <div class="mt-4">
            <Warning
              warning_message={`There are only ${score_summary.dataset_size} item(s) in your Eval Method Dataset. This is generally too small to get a good sense of how well your eval-configs perform.`}
              warning_color="warning"
              tight={true}
            />
          </div>
        {/if}
      </div>
    </div>
    <div class="mt-16">
      {#if eval_configs?.length}
        <div class="flex flex-col lg:flex-row gap-4 lg:gap-8 mb-6">
          <div class="grow">
            <div class="text-xl font-bold">Correlation to Human Ratings</div>
            <div class="text-xs text-gray-500">
              How each eval method correlates to human ratings.
              <button
                class="link"
                on:click={() => {
                  score_legend_dialog?.show()
                }}
              >
                Learn about score types.
              </button>
            </div>
            {#if score_summary_error}
              <div class="text-error text-sm">
                {score_summary_error.getMessage() ||
                  "An unknown error occurred fetching scores."}
              </div>
            {/if}
          </div>
          <div class="flex flex-row gap-2">
            <FormElement
              id="score-type"
              label="Score"
              hide_label={true}
              inputType="select"
              select_options={[
                ["norm_mse", "Normalized Mean Squared Error"],
                ["norm_mae", "Normalized Mean Absolute Error"],
                ["mse", "Mean Squared Error"],
                ["mae", "Mean Absolute Error"],
              ]}
              bind:value={score_type}
            />
            <div class="mt-1">
              <RunEval
                btn_size="normal"
                bind:run_url={run_eval_url}
                on_run_complete={() => {
                  get_score_summary()
                }}
              />
            </div>
          </div>
        </div>

        <!-- Warn the user if some evals are incomplete -->

        {#if incomplete_warning(score_summary).length}
          <div class="mt-6 mb-4">
            <Warning
              warning_message={`There are issues you should resolve before analyzing this data.`}
              tight={true}
            />
            <ul class="list-disc list-inside text-sm text-gray-500 pl-2 pt-2">
              {#each incomplete_warning(score_summary) as warning}
                <li>{warning}</li>
              {/each}
            </ul>
          </div>
        {/if}

        <div class="overflow-x-auto rounded-lg border">
          <table class="table">
            <thead>
              <tr>
                <th>
                  <div>Eval Method</div>
                  <div class="font-normal">How task output is evaluated</div>
                </th>
                <th> Eval Instructions </th>
                {#each evaluator.output_scores as output_score}
                  <th class="text-center">
                    {output_score.name}
                    <span class="ml-[-5px]">
                      <InfoTooltip
                        tooltip_text={info_tooltip_text(
                          output_score.type,
                          score_type,
                        )}
                      />
                    </span>
                  </th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each eval_configs || [] as eval_config}
                {@const percent_complete =
                  score_summary?.eval_config_percent_complete?.[
                    "" + eval_config.id
                  ]}
                <tr>
                  <td>
                    <div class="font-medium">
                      {eval_config.name}
                    </div>
                    <div class="text-sm text-gray-500">
                      {eval_config_to_ui_name(eval_config.config_type)}
                    </div>
                    <div class="text-sm text-gray-500">
                      {model_name(
                        eval_config?.model.properties?.["model_name"],
                        $model_info,
                      )}
                    </div>
                    <div class="text-sm text-gray-500">
                      {provider_name_from_id(
                        eval_config?.model.properties?.["model_provider"] + "",
                      )}
                    </div>
                    {#if percent_complete}
                      <div
                        class="text-sm {percent_complete < 1.0
                          ? 'text-error'
                          : 'text-gray-500'}"
                      >
                        {(percent_complete * 100.0).toFixed(1)}% complete
                      </div>
                    {:else if score_summary}
                      <!-- We have results, but not for this run config -->
                      <div class="text-sm text-error">0% complete</div>
                    {/if}
                    {#if eval_config.id == evaluator.current_config_id}
                      <div class="badge badge-primary mt-2">Default</div>
                    {:else}
                      <button
                        class="link text-sm text-gray-500"
                        on:click={() => {
                          set_current_eval_config(eval_config.id)
                        }}
                      >
                        Set as default
                      </button>
                    {/if}
                  </td>
                  <td>
                    <div class="max-w-[600px] min-w-[200px]">
                      <div class="max-h-[140px] overflow-y-hidden relative">
                        <EvalConfigInstruction {eval_config} />
                        <div class="absolute bottom-0 left-0 w-full">
                          <div
                            class="h-36 bg-gradient-to-t from-white to-transparent"
                          ></div>
                          <div
                            class="text-center bg-white font-medium font-sm text-gray-500"
                          >
                            <button
                              class="text-gray-500"
                              on:click={() => {
                                displayed_eval_config = eval_config
                                eval_config_instructions_dialog?.show()
                              }}
                            >
                              See all
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </td>
                  {#each evaluator.output_scores as output_score}
                    {@const scores =
                      score_summary?.results?.["" + eval_config.id]?.[
                        string_to_json_key(output_score.name)
                      ]}
                    <td class="text-center min-w-[115px]">
                      {#if scores}
                        {#if score_type === "mae"}
                          {scores.mean_absolute_error.toFixed(2)}
                        {:else if score_type === "mse"}
                          {scores.mean_squared_error.toFixed(2)}
                        {:else if score_type === "norm_mse"}
                          {scores.mean_normalized_squared_error.toFixed(3)}
                        {:else if score_type === "norm_mae"}
                          {scores.mean_normalized_absolute_error.toFixed(3)}
                        {/if}
                      {:else}
                        unknown
                      {/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <!-- TODO error case here-->
      {/if}
    </div>
  {/if}
</AppPage>

<Dialog
  bind:this={eval_config_instructions_dialog}
  title="Eval Method Instructions: {displayed_eval_config?.name}"
  action_buttons={[
    {
      label: "Close",
      isCancel: true,
    },
  ]}
>
  <EvalConfigInstruction bind:eval_config={displayed_eval_config} />
</Dialog>

<Dialog
  bind:this={score_legend_dialog}
  title="Score Legend"
  action_buttons={[
    {
      label: "Close",
      isCancel: true,
    },
  ]}
>
  <div class="font-medium text-sm text-gray-500">
    Each score is a correlation score between the evaluator's score and the
    human score added through the dataset tab.
  </div>
  <div class="font-medium mt-5">Mean Absolute Error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light text-sm">
    Example: If a human scores an item a 3, and the eval scores it a 5, the
    absolute error would be 2 [abs(3-5)]. The overall score is the mean of all
    absolute errors.
  </div>
  <div class="font-medium mt-6">Normalized Mean Absolute Error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light text-sm">
    Like mean absolute error, but scores are normalized to the range 0-1. For
    example, for a 1-5 star rating, 1-star is score 0 and 5-star is score 1.
  </div>
  <div class="font-medium mt-6">Mean Squared Error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light text-sm">
    Example: If a human scores an item a 3, and the eval scores it a 5, the
    squared error would be 4 [(3-5)^2]. The overall score is the mean of all
    squared errors. This imporoves over absolute error as it penalizes larger
    errors more.
  </div>
  <div class="font-medium mt-6">Normalized Mean Squared Error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light text-sm">
    Like mean squared error, but scores are normalized to the range 0-1. For
    example, for a 1-5 star rating, 1-star is score 0 and 5-star is score 1.
  </div>
</Dialog>

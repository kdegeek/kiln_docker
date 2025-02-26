<script lang="ts">
  import AppPage from "../../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client, base_url } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import RunEval from "./../run_eval.svelte"
  import type { EvalConfig, EvalConfigCompareSummary } from "$lib/types"
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
    ])
    // These can be parallel
    get_eval()
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
      eval_configs = data
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
      name: "Eval Name",
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
      name: "Config Eval Set",
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
        "No items in your eval-config dataset. Generate some runs in your dataset tab, and tag them to add them to your eval-config dataset.",
      )
    }
    if (score_summary.not_rated_count > 0) {
      warnings.push(
        `${score_summary.not_rated_count} item(s) in your eval-config dataset are not rated at all. Add human ratings to these items in the dataset tab.`,
      )
    }
    if (score_summary.partially_rated_count > 0) {
      warnings.push(
        `${score_summary.partially_rated_count} item(s) in your eval-config dataset are only partially rated. Add human ratings to these items in the dataset tab for each score.`,
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
</script>

<AppPage
  title="Compare Eval Configs"
  subtitle="Find the evaluator that best matches human-ratings"
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
      </div>
    </div>
    <div class="mt-16">
      {#if eval_configs?.length}
        <div class="flex flex-col lg:flex-row gap-4 lg:gap-8 mb-6">
          <div class="grow">
            <div class="text-xl font-bold">Correlation to Human Scores</div>
            <div class="text-xs text-gray-500">
              How each eval config correlates to human scores (ratings from the
              dataset tab).
            </div>
            {#if score_summary_error}
              <div class="text-error text-sm">
                {score_summary_error.getMessage() ||
                  "An unknown error occurred fetching scores."}
              </div>
            {/if}
          </div>
          <div>
            <button
              class="btn btn-mid mr-2"
              on:click={() => {
                score_legend_dialog?.show()
              }}
            >
              Score Legend
            </button>
            <RunEval
              bind:run_url={run_eval_url}
              on_run_complete={() => {
                get_score_summary()
              }}
            />
          </div>
        </div>

        <!-- Warn the user if some evals are incomplete -->
        {#if incomplete_warning(score_summary).length}
          <div class="mt-6 mb-4">
            <Warning
              warning_message={`There are issues you should resolve before analyzing this data.`}
              tight={true}
            />
            <ul class="list-disc list-inside text-error">
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
                  <div>Eval Config</div>
                  <div class="font-normal">How task output is evaluated</div>
                </th>
                <th> Eval Instructions </th>
                {#each evaluator.output_scores as output_score}
                  <th class="text-center">
                    {output_score.name}
                    <div class="font-normal">
                      {#if output_score.type === "five_star"}
                        1 to 5
                        <span class="ml-[-5px]">
                          <InfoTooltip
                            tooltip_text="1 to 5 stars, where 5 is best"
                          />
                        </span>
                      {:else if output_score.type === "pass_fail"}
                        pass/fail
                        <span class="ml-[-5px]">
                          <InfoTooltip tooltip_text="0 is fail and 1 is pass" />
                        </span>
                      {:else if output_score.type === "pass_fail_critical"}
                        pass/fail/critical
                        <span class="ml-[-5px]">
                          <InfoTooltip
                            tooltip_text="-1 is critical failure, 0 is fail, and 1 is pass"
                          />
                        </span>
                      {:else}
                        {output_score.type}
                      {/if}
                    </div>
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
                        <div>
                          MAE: {scores.mean_absolute_error.toFixed(2)}
                        </div>
                        <div>
                          MSE: {scores.mean_squared_error.toFixed(2)}
                        </div>
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
  title="Eval Config Instructions: {displayed_eval_config?.name}"
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
  <div class="font-medium mt-4">MAE: Mean Absolute Error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light">
    Example: If the eval scores an item a 3, and the eval scores it a 5, the
    absolute error would be 2 [abs(3-5)]. The overall score is the mean of all
    absolute errors.
  </div>
  <div class="font-medium mt-6">MSE: Mean squared error</div>
  <div class="text-sm text-gray-500 font-medium mb-1">Lower is better</div>
  <div class="font-light">
    Example: If the eval scores an item a 3, and the eval scores it a 5, the
    squared error would be 4 [(3-5)^2]. The overall score is the mean of all
    squared errors.
  </div>
</Dialog>

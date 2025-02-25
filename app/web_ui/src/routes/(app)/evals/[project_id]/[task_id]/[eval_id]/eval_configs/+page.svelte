<script lang="ts">
  import AppPage from "../../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client, base_url } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import FormElement from "$lib/utils/form_element.svelte"
  import type {
    EvalConfig,
    EvalConfigType,
    ProviderModels,
    EvalConfigCompareSummary,
  } from "$lib/types"
  import { goto } from "$app/navigation"
  import {
    model_info,
    load_model_info,
    model_name,
    provider_name_from_id,
    prompt_name_from_id,
    load_available_prompts,
    load_available_models,
  } from "$lib/stores"
  import Dialog from "$lib/ui/dialog.svelte"
  import Warning from "$lib/ui/warning.svelte"
  import { string_to_json_key } from "$lib/utils/json_schema_editor/json_schema_templates"
  import InfoTooltip from "$lib/ui/info_tooltip.svelte"

  let evaluator: Eval | null = null
  let eval_error: KilnError | null = null
  let eval_loading = true

  let eval_configs: EvalConfig[] | null = null
  let eval_configs_error: KilnError | null = null
  let eval_configs_loading = true

  let score_summary: EvalConfigCompareSummary | null = null
  let score_summary_error: KilnError | null = null
  let score_summary_loading = false

  $: loading = eval_loading || eval_configs_loading || score_summary_loading
  $: error = eval_error || eval_configs_error || score_summary_error

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

  let run_dialog: Dialog | null = null
  let running_progress_dialog: Dialog | null = null

  let eval_run_error: KilnError | null = null
  let eval_state:
    | "not_started"
    | "running"
    | "complete"
    | "complete_with_errors" = "not_started"
  let eval_complete_count = 0
  let eval_total_count = 0
  let eval_error_count = 0

  function run_eval(): boolean {
    score_summary = null
    eval_state = "running"
    eval_complete_count = 0
    eval_total_count = 0
    eval_error_count = 0

    const eventSource = new EventSource(
      `${base_url}/api/projects/${project_id}/tasks/${task_id}/eval/${eval_id}/eval_config/${current_eval_config_id}/run?all_run_configs=true`,
    )

    eventSource.onmessage = (event) => {
      try {
        if (event.data === "complete") {
          // Special end message
          eventSource.close()
          eval_state =
            eval_error_count > 0 ? "complete_with_errors" : "complete"
          get_score_summary()
        } else {
          const data = JSON.parse(event.data)
          eval_complete_count = data.progress
          eval_total_count = data.total
          eval_error_count = data.errors
          eval_state = "running"
        }
      } catch (error) {
        eval_run_error = createKilnError(error)
        eval_state = "complete_with_errors"
        get_score_summary()
      }
    }

    // Don't restart on an error (default SSE behavior)
    eventSource.onerror = (error) => {
      eventSource.close()
      eval_state = "complete_with_errors"
      eval_run_error = createKilnError(error)
      get_score_summary()
    }

    // Switch over to the progress dialog, closing the run dialog
    running_progress_dialog?.show()
    return true
  }

  // TODO P0: adapt this from other screen, to this screen. warning if len(results) == 0, no items in dataset (dataset_size == 0), and other "go fix your dataset" warnings
  function show_incomplete_warning(
    score_summary: EvalResultSummary | null,
  ): boolean {
    if (!score_summary?.run_config_percent_complete) {
      return false
    }
    return false

    const values = Object.values(score_summary.run_config_percent_complete)
    const minComplete =
      values.length > 0
        ? values.reduce((min, val) => Math.min(min, val), 1.0)
        : 1.0
    return minComplete < 1.0
  }
</script>

<AppPage title="Compare Eval Configs" subtitle={evaluator?.name}>
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
              Overview of how each eval config correlates to human scores
              (ratings from the dataset tab).
            </div>
            {#if score_summary_error}
              <div class="text-error text-sm">
                {score_summary_error.getMessage() ||
                  "An unknown error occurred fetching scores."}
              </div>
            {/if}
          </div>
          <div>
            {#if eval_state === "not_started"}
              <button
                class="btn btn-mid btn-primary"
                on:click={() => {
                  run_dialog?.show()
                }}>Run Eval</button
              >
            {:else}
              <button
                class="btn btn-mid"
                on:click={() => {
                  running_progress_dialog?.show()
                }}
              >
                {#if eval_state === "running"}
                  <div class="loading loading-spinner loading-xs"></div>
                  Running...
                {:else if eval_state === "complete"}
                  Eval Complete
                {:else if eval_state === "complete_with_errors"}
                  Eval Complete with Errors
                {:else}
                  Eval Status
                {/if}
              </button>
            {/if}
          </div>
        </div>

        <!-- Warn the user if some evals are incomplete -->
        <!-- TODO more cases to explain here: needs rating, needs content, need eval run, etc-->
        {#if show_incomplete_warning(score_summary)}
          <div class="mt-6 mb-4">
            <button
              class="tooltip tooltip-top cursor-pointer"
              data-tip="Running evals will update any missing dataset items, without re-running complete items. If some evals consistently fail, check the logs; it is likely that the model is failing on the task or the eval."
            >
              <Warning
                warning_message={`Some evals are incomplete and should be excluded from analysis. Run evals to complete their dataset.`}
                tight={true}
              />
            </button>
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
                      {model_name(
                        eval_config?.model.properties?.["model_name"],
                        $model_info,
                      )}
                    </div>
                    <div class="text-sm text-gray-500">
                      {provider_name_from_id(
                        eval_config?.model.properties?.["model_provider_name"] +
                          "",
                      )}
                    </div>
                    {#if percent_complete}
                      <div
                        class="text-sm {percent_complete < 1.0
                          ? 'text-error'
                          : 'text-gray-500'}"
                      >
                        Eval {(percent_complete * 100.0).toFixed(1)}% complete
                      </div>
                    {:else if score_summary}
                      <!-- We have results, but not for this run config -->
                      <div class="text-sm text-error">Eval 0% complete</div>
                    {/if}
                  </td>
                  <td>
                    <div class="max-w-[600px] min-w-[300px]">
                      {#if eval_config.properties?.["task_description"]}
                        <div class="text-sm mb-4">
                          <div class="font-medium mb-2">Task Description:</div>
                          {eval_config.properties["task_description"]}
                        </div>
                      {/if}
                      {#if eval_config.properties?.["eval_steps"] && Array.isArray(eval_config.properties["eval_steps"])}
                        <div class="text-sm">
                          <div class="font-medium mb-2">
                            Evaluator Instructions:
                          </div>
                          <ol class="list-decimal">
                            {#each eval_config.properties["eval_steps"] as step}
                              <li>
                                <span class="whitespace-pre-line">
                                  {step}
                                </span>
                              </li>
                            {/each}
                          </ol>
                        </div>
                      {/if}
                    </div>
                  </td>
                  {#each evaluator.output_scores as output_score}
                    {@const score = null}
                    <td class="text-center">
                      {score != null ? score.toFixed(2) : "unknown"}
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
  bind:this={running_progress_dialog}
  title="Eval Progress"
  action_buttons={eval_state === "complete" ||
  eval_state === "complete_with_errors"
    ? [
        {
          label: "Close",
          isCancel: true,
          isPrimary: false,
        },
      ]
    : []}
>
  <div
    class="mt-12 mb-6 flex flex-col items-center justify-center min-h-[100px] text-center"
  >
    {#if eval_state === "complete"}
      <div class="font-medium">Eval Complete 🎉</div>
      {#if eval_total_count == 0}
        <div class="text-gray-500 text-sm mt-2">
          No evals were run, because everything was already up to date!
        </div>
      {/if}
    {:else if eval_state === "complete_with_errors"}
      <div class="font-medium">Eval Complete with Errors</div>
    {:else if eval_state === "running"}
      <div class="loading loading-spinner loading-lg text-success"></div>
      <div class="font-medium mt-4">Running...</div>
    {/if}
    <div class="text-sm font-light min-w-[120px]">
      {#if eval_total_count > 0}
        <div>
          {eval_complete_count + eval_error_count} of {eval_total_count}
        </div>
      {/if}
      {#if eval_error_count > 0}
        <div class="text-error font-light text-xs">
          {eval_error_count} error{eval_error_count === 1 ? "" : "s"}
        </div>
      {/if}
      {#if eval_run_error}
        <div class="text-error font-light text-xs mt-2">
          {eval_run_error.getMessage() || "An unknown error occurred"}
        </div>
      {/if}
    </div>
  </div>
</Dialog>

<Dialog
  bind:this={run_dialog}
  title="Run Eval"
  action_buttons={[
    {
      label: "Cancel",
      isCancel: true,
    },
    {
      label: "Run Eval",
      action: run_eval,
      isPrimary: true,
    },
  ]}
>
  <div class="flex flex-col gap-2 font-light mt-4">
    <div>Run this eval with the selected configuration?</div>
    <div>Don't close this page if you want to monitor progress.</div>
    <Warning
      warning_color="warning"
      warning_message="This may use considerable compute/credits."
      tight={true}
    />
  </div>
</Dialog>

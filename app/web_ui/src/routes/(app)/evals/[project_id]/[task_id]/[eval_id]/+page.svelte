<script lang="ts">
  import AppPage from "../../../../app_page.svelte"
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
    TaskRunConfig,
    EvalResultSummary,
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
  import AvailableModelsDropdown from "../../../../run/available_models_dropdown.svelte"
  import PromptTypeSelector from "../../../../run/prompt_type_selector.svelte"
  import Warning from "$lib/ui/warning.svelte"
  import { title_to_name } from "$lib/utils/json_schema_editor/json_schema_templates"

  $: project_id = $page.params.project_id
  $: task_id = $page.params.task_id
  $: eval_id = $page.params.eval_id

  let evaluator: Eval | null = null
  let eval_error: KilnError | null = null
  let eval_loading = true

  let eval_configs: EvalConfig[] | null = null
  let eval_configs_error: KilnError | null = null
  let eval_configs_loading = true
  let current_eval_config_id: string | null = null

  let task_run_configs: TaskRunConfig[] | null = null
  let task_run_configs_error: KilnError | null = null
  let task_run_configs_loading = true

  let score_summary: EvalResultSummary | null = null
  let score_summary_error: KilnError | null = null
  let score_summary_loading = false

  $: loading =
    eval_loading ||
    eval_configs_loading ||
    task_run_configs_loading ||
    score_summary_loading
  $: error = eval_error || eval_configs_error || task_run_configs_error
  // Note: not including score_summary_error, because it's not a critical error we should block the UI for

  onMount(async () => {
    // Wait for page params to load
    await tick()
    // Wait for these 3 to load, as they are needed for better labels. Usually already cached and instant.
    await Promise.all([
      load_model_info(),
      load_available_prompts(),
      load_available_models(),
    ])
    // Get the eval first (want it to set the current config id), then the rest in parallel
    await get_eval()
    // These two can be parallel
    await Promise.all([get_eval_configs(), get_task_run_configs()])
    // This needs the selected eval config id
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
      // Set the selected eval config: prefer query params, then eval's default, then
      current_eval_config_id =
        $page.url.searchParams.get("selected_eval_config") ||
        evaluator.current_config_id ||
        null
    } catch (error) {
      eval_error = createKilnError(error)
    } finally {
      eval_loading = false
    }
  }

  async function get_eval_configs() {
    try {
      eval_configs_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_configs",
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
      eval_configs = data
      // This may be already set by evaluator loading, if so we prioritize that, but fallback to first
      if (
        !current_eval_config_id &&
        eval_configs.length > 0 &&
        eval_configs[0].id
      ) {
        current_eval_config_id = eval_configs[0].id
      }
    } catch (error) {
      eval_configs_error = createKilnError(error)
    } finally {
      eval_configs_loading = false
    }
  }

  async function get_task_run_configs() {
    try {
      task_run_configs_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/task_run_configs",
        {
          params: {
            path: {
              project_id,
              task_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      task_run_configs = data
    } catch (error) {
      task_run_configs_error = createKilnError(error)
    } finally {
      task_run_configs_loading = false
    }
  }

  async function get_score_summary() {
    if (!current_eval_config_id) {
      score_summary_error = new KilnError("No eval config selected", null)
      return
    }
    try {
      score_summary_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_config/{eval_config_id}/score_summary",
        {
          params: {
            path: {
              project_id,
              task_id,
              eval_id,
              eval_config_id: current_eval_config_id,
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

  // Watches the current eval config id
  $: watch_selected_eval_config(current_eval_config_id)
  function watch_selected_eval_config(selected_id: string | null) {
    if (selected_id === "add_config") {
      // if it's "add_config" then navigates to the create eval config page
      goto(`/evals/${project_id}/${task_id}/${eval_id}/create_eval_config`)
      return
    }
    // If the selected id is not null, then get the score summary
    score_summary = null
    if (selected_id) {
      get_score_summary()
    }
  }

  type UiProperty = {
    name: string
    value: string
  }

  function eval_config_to_ui_name(eval_config_type: EvalConfigType): string {
    return (
      {
        g_eval: "G-Eval",
        llm_as_judge: "LLM as Judge",
      }[eval_config_type] || eval_config_type
    )
  }

  // A name for the eval config that is human readable and helpful
  // Combine's it's memorable name with it's properties
  function get_eval_config_name(
    eval_config: EvalConfig,
    model_info: ProviderModels | null,
  ): string {
    let parts = []
    parts.push(eval_config_to_ui_name(eval_config.config_type))
    parts.push(
      model_name(eval_config.model.properties["model_name"], model_info),
    )
    parts.push(prompt_name_from_id(eval_config.prompt.name))
    return eval_config.name + " — " + parts.join(", ")
  }

  function get_eval_properties(
    evaluator: Eval,
    score_summary: EvalResultSummary | null,
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
    let outputs = []
    for (const output of evaluator.output_scores) {
      outputs.push(output.name + " (" + output.type + ")")
    }
    if (outputs.length > 0) {
      properties.push({
        name: "Output Scores",
        value: outputs.join(", "),
      })
    }
    let eval_set_size = ""
    if (score_summary) {
      eval_set_size = " (" + score_summary.dataset_size + " items)"
    }
    properties.push({
      name: "Eval Set",
      value: evaluator.eval_set_filter_id + eval_set_size,
    })
    properties.push({
      name: "Config Eval Set",
      value: evaluator.eval_configs_filter_id,
    })
    return properties
  }

  function get_eval_config_properties(
    eval_config_id: string | null,
    model_info: ProviderModels | null,
  ): UiProperty[] {
    const eval_config = eval_configs?.find(
      (config) => config.id === eval_config_id,
    )
    if (!eval_config) {
      return [
        {
          name: "No Config Selected",
          value: "Select a config from dropdown above",
        },
      ]
    }

    const properties: UiProperty[] = []

    properties.push({
      name: "Type",
      value: eval_config_to_ui_name(eval_config.config_type),
    })
    properties.push({
      name: "Eval Model",
      value: model_name(
        eval_config.model.properties["model_name"] + "",
        model_info,
      ),
    })
    properties.push({
      name: "Eval Provider",
      value: provider_name_from_id(
        eval_config.model.properties["model_provider"] + "",
      ),
    })
    // TODO remove this once we consolidate prompts
    properties.push({
      name: "Prompt",
      value: prompt_name_from_id(eval_config.prompt.name + ""),
    })
    return properties
  }

  function get_eval_config_select_options(
    configs: EvalConfig[] | null,
  ): [string, [unknown, string][]][] {
    const configs_options: [string, string][] = []
    for (const c of configs || []) {
      if (c.id) {
        configs_options.push([c.id, get_eval_config_name(c, $model_info)])
      }
    }

    const results: [string, [unknown, string][]][] = []
    if (configs_options.length > 0) {
      results.push(["Select Eval Config", configs_options])
    }
    results.push(["Manage Eval Configs", [["add_config", "Add Eval Config"]]])
    return results
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
    if (!current_eval_config_id) {
      eval_run_error = new KilnError("No eval config selected", null)
      eval_state = "complete_with_errors"
      // True to close the run dialog, and then show the error in the progress dialog
      running_progress_dialog?.show()
      return true
    }

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

  let task_run_config_model_name = ""
  let task_run_config_provider_name = ""
  let task_run_config_prompt_method = "simple_prompt_builder"

  let add_task_config_dialog: Dialog | null = null
  let add_task_config_error: KilnError | null = null
  async function add_task_config(): Promise<boolean> {
    if (
      !task_run_config_model_name ||
      !task_run_config_provider_name ||
      !task_run_config_prompt_method
    ) {
      add_task_config_error = new KilnError("Missing required fields", null)
      return false
    }

    try {
      const { error } = await client.POST(
        "/api/projects/{project_id}/tasks/{task_id}/task_run_config",
        {
          params: {
            path: {
              project_id,
              task_id,
            },
          },
          body: {
            model_name: task_run_config_model_name,
            // @ts-expect-error not checking types here, server will check them
            model_provider_name: task_run_config_provider_name,
            prompt_id: task_run_config_prompt_method,
          },
        },
      )
      if (error) {
        throw error
      }
      // Load the updated list of task run configs after success
      get_task_run_configs()
    } catch (error) {
      add_task_config_error = createKilnError(error)
      return false
    }
    return true
  }

  function show_incomplete_warning(
    score_summary: EvalResultSummary | null,
  ): boolean {
    if (!score_summary?.run_config_percent_complete) {
      return false
    }

    const values = Object.values(score_summary.run_config_percent_complete)
    const minComplete =
      values.length > 0
        ? values.reduce((min, val) => Math.min(min, val), 1.0)
        : 1.0
    return minComplete < 1.0
  }
</script>

<AppPage
  title="Evaluator"
  subtitle={evaluator?.name}
  action_buttons={[
    {
      label: "Evaluate Eval Quality",
      href: `/evals/${project_id}/${task_id}/${eval_id}/TODO`,
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
      <div class="grow basis-1/2">
        <div class="text-xl font-bold mb-4">Properties</div>
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
      <div class="grow basis-1/2 flex flex-col gap-4">
        <div>
          <div class="text-xl font-bold mb-2">Config</div>

          <FormElement
            hide_label={true}
            id="eval_config_select"
            label="Eval Config"
            inputType="select"
            bind:value={current_eval_config_id}
            select_options_grouped={get_eval_config_select_options(
              eval_configs,
            )}
          />
        </div>
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each get_eval_config_properties(current_eval_config_id, $model_info) as property}
            <div class="flex items-center">{property.name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {property.value}
            </div>
          {/each}
          <div class="flex items-center">Config Quality</div>
          <div class="flex items-center text-gray-500 overflow-x-hidden">
            <a href="TODO" class="link"> Compare and optimize </a>
          </div>
        </div>
      </div>
    </div>
    <div class="mt-16">
      {#if task_run_configs?.length}
        <div class="flex flex-col lg:flex-row gap-4 lg:gap-8 mb-6">
          <div class="grow">
            <div class="text-xl font-bold">Results</div>
            <div class="text-xs text-gray-500">
              Filtered by the selected eval config. Rows are grouped by task run
              config.
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
                class="btn btn-mid mr-2"
                on:click={() => {
                  add_task_config_dialog?.show()
                }}>Add Run Config</button
              >
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
        {#if show_incomplete_warning(score_summary)}
          <div class="mt-6 mb-4">
            <button
              class="tooltip tooltip-top cursor-pointer"
              data-tip="Running evals will update any missing dataset items, without re-running complete items. If some evals consistently fail, check the logs; tt's possible the model is failing on the task, or the eval."
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
                <th> Run Config </th>
                {#each evaluator.output_scores as output_score}
                  <th class="text-center">
                    {output_score.name}
                    {#if output_score.type === "five_star"}
                      (1 to 5)
                    {:else if output_score.type === "pass_fail"}
                      (0 to 1)
                    {:else if output_score.type === "pass_fail_critical"}
                      (-1 to 1)
                    {:else}
                      ({output_score.type})
                    {/if}
                  </th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each task_run_configs || [] as task_run_config}
                {@const percent_complete =
                  score_summary?.run_config_percent_complete?.[
                    "" + task_run_config.id
                  ]}
                <tr
                  class="hover cursor-pointer"
                  on:click={() => {
                    console.log("TODO: link")
                  }}
                >
                  <td>
                    <div class="font-medium">
                      {task_run_config.name}
                    </div>
                    <div class="text-sm text-gray-500">
                      {model_name(
                        task_run_config?.run_config_properties?.model_name,
                        $model_info,
                      )}
                    </div>
                    <div class="text-sm text-gray-500">
                      {provider_name_from_id(
                        task_run_config?.run_config_properties
                          ?.model_provider_name,
                      )}
                    </div>
                    <div class="text-sm text-gray-500">
                      {prompt_name_from_id(
                        task_run_config?.run_config_properties?.prompt_id,
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
                  {#each evaluator.output_scores as output_score}
                    {@const score =
                      score_summary?.results?.["" + task_run_config.id]?.[
                        title_to_name(output_score.name)
                      ]?.mean_score}
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
        <div class="text-xl font-bold">Results</div>
        <div
          class="font-light text-sm max-w-[400px] mx-auto flex flex-col gap-2 mt-8"
        >
          <div class="font-medium text-lg">Create a Run Config</div>
          <div>
            A task run config defines how the task is run, such as which model
            and prompt to use. Create one to run this evaluator.
          </div>
          <button
            class="btn btn-primary"
            on:click={() => {
              add_task_config_dialog?.show()
            }}
          >
            Add Task Config
          </button>
        </div>
      {/if}
    </div>
  {/if}
</AppPage>

<Dialog
  bind:this={add_task_config_dialog}
  title="Add a Task Run Config"
  action_buttons={[
    {
      label: "Cancel",
      isCancel: true,
    },
    {
      label: "Create",
      isPrimary: true,
      asyncAction: add_task_config,
    },
  ]}
>
  <h4 class="text-sm text-gray-500">
    Create a task run config, defining a way to run this task (model+prompt).
  </h4>
  <h4 class="text-sm text-gray-500 mt-1">
    Your evaluator can compare multiple run configs to find the best one for
    running this task.
  </h4>
  <div class="flex flex-col gap-2 pt-6">
    <AvailableModelsDropdown
      bind:model_name={task_run_config_model_name}
      bind:provider_name={task_run_config_provider_name}
    />
    <PromptTypeSelector bind:prompt_method={task_run_config_prompt_method} />
    {#if add_task_config_error}
      <div class="text-error text-sm">
        {add_task_config_error.getMessage() || "An unknown error occurred"}
      </div>
    {/if}
  </div>
</Dialog>

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

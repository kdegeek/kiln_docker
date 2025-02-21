<script lang="ts">
  import AppPage from "../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import { formatDate } from "$lib/utils/formatters"
  import FormElement from "$lib/utils/form_element.svelte"
  import type { EvalConfig, EvalConfigType } from "$lib/types"

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

  $: loading = eval_loading || eval_configs_loading
  $: error = eval_error || eval_configs_error

  onMount(async () => {
    // Wait for params to load
    await tick()
    // Can actually do these in parallel
    get_eval()
    get_eval_configs()
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
      if (evaluator.current_config_id) {
        current_eval_config_id = evaluator.current_config_id
      }
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
      // This may be already set by evaluator.current_config_id, if so we prioritize that
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

  $: add_eval_config(current_eval_config_id)
  let last_selected_valid_id: string | null = null

  function add_eval_config(selected_id: string | null) {
    if (selected_id !== "add_config") {
      last_selected_valid_id = selected_id
      return
    }

    // Reset the selected id, so we don't leave "add_config" selected
    current_eval_config_id = last_selected_valid_id
    alert("Not implemented")
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

  function get_eval_config_name(eval_config: EvalConfig): string {
    let name = eval_config_to_ui_name(eval_config.config_type)
    let parts = []
    parts.push(eval_config.model.properties["model_name"])
    parts.push(eval_config.prompt.name)
    return name + " (" + parts.join(", ") + ")"
  }

  function get_eval_properties(evaluator: Eval): UiProperty[] {
    const properties: UiProperty[] = []

    properties.push({
      name: "Name",
      value: evaluator.name,
    })
    properties.push({
      name: "ID",
      value: evaluator.id || "unknown",
    })
    if (evaluator.description) {
      properties.push({
        name: "Description",
        value: evaluator.description,
      })
    }
    if (evaluator.created_at) {
      properties.push({
        name: "Created At",
        value: formatDate(evaluator.created_at),
      })
    }
    let outputs = []
    for (const output of evaluator.output_scores) {
      outputs.push(output.name + " (" + output.type + ")")
    }
    if (outputs.length > 0) {
      properties.push({
        name: "Outputs",
        value: outputs.join(", "),
      })
    }
    return properties
  }
  function get_eval_config_properties(
    eval_config_id: string | null,
  ): UiProperty[] {
    if (!eval_config_id) {
      return []
    }
    const eval_config = eval_configs?.find(
      (config) => config.id === eval_config_id,
    )
    if (!eval_config) {
      return []
    }
    const properties: UiProperty[] = []

    properties.push({
      name: "Type",
      value: eval_config_to_ui_name(eval_config.config_type),
    })
    properties.push({
      name: "Model",
      value: eval_config.model.properties["model_name"] + "",
    })
    properties.push({
      name: "Provider",
      value: eval_config.model.properties["model_provider"] + "",
    })
    properties.push({
      name: "Prompt",
      value: eval_config.prompt.name + "",
    })
    return properties
  }

  function get_eval_config_select_options(
    configs: EvalConfig[] | null,
  ): [string, string][] {
    if (!configs) {
      return []
    }
    const results: [string, string][] = []
    for (const c of configs) {
      if (c.id) {
        results.push([c.id, get_eval_config_name(c)])
      }
    }
    results.push(["add_config", "Add Config"])
    return results
  }
</script>

<AppPage title="Evaluator" sub_subtitle={evaluator?.name}>
  {#if loading}
    <div class="w-full min-h-[50vh] flex justify-center items-center">
      <div class="loading loading-spinner loading-lg"></div>
    </div>
  {:else if error}
    <div
      class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
    >
      <div class="font-medium">Error Loading Evaluators</div>
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
          {#each get_eval_properties(evaluator) as property}
            <div class="flex items-center">{property.name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {property.value}
            </div>
          {/each}
        </div>
      </div>
      <div class="grow basis-1/2 flex flex-col gap-4">
        <div>
          <div class="text-xl font-bold">Eval Config</div>
          <div class="text-xs text-gray-500">
            How this evaluator will be run.
          </div>
        </div>
        <FormElement
          hide_label={true}
          id="eval_config_select"
          label="Eval Config"
          inputType="select"
          bind:value={current_eval_config_id}
          select_options={get_eval_config_select_options(eval_configs)}
        />
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each get_eval_config_properties(current_eval_config_id) as property}
            <div class="flex items-center">{property.name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {property.value}
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</AppPage>

<script lang="ts">
  import AppPage from "../../../../app_page.svelte"
  import type { Eval } from "$lib/types"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import type { EvalProgress } from "$lib/types"

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
    if (eval_progress) {
      eval_set_size = " (" + eval_progress.dataset_size + " items)"
    }
    properties.push({
      name: "Eval Dataset",
      value: evaluator.eval_set_filter_id + eval_set_size,
    })
    properties.push({
      name: "Eval Method Dataset",
      value: evaluator.eval_configs_filter_id,
    })
    return properties
  }

  $: has_default_eval_config = evaluator && evaluator.current_config_id

  let edit_dialog: EditDialog | null = null
</script>

<AppPage
  title="Evaluator"
  subtitle={evaluator?.name}
  action_buttons={[
    {
      label: "Edit",
      handler: () => {
        edit_dialog?.show()
      },
    },
    {
      label: "Compare Evaluation Methods",
      href: `/evals/${project_id}/${task_id}/${eval_id}/eval_configs`,
      primary: !has_default_eval_config,
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
        <ul class="steps steps-vertical ml-4">
          <li class="step step-primary" data-content="✓">Define Goals</li>
          <li class="step step-primary" data-content="✓">Create Eval Data</li>
          <li class="step step-primary" data-content="✓">Rate Eval Data</li>
          <li class="step" data-content="">Find Ideal Eval Method</li>
          <li class="step" data-content="">
            <a
              class="link"
              href={`/evals/${project_id}/${task_id}/${eval_id}/compare_run_methods`}
              >Find Ideal Way to Run Task</a
            >
          </li>
        </ul>
      </div>
      <div class="grow basis-1/2">
        <div class="text-xl font-bold mb-4">Evaluator Properties</div>
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each get_eval_properties(evaluator, eval_progress) as property}
            <div class="flex items-center">{property.name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {property.value}
            </div>
          {/each}
        </div>
        {#if eval_progress && eval_progress.dataset_size > 0 && eval_progress.dataset_size < 25}
          <div class="mt-4">
            <Warning
              warning_message={`There are only ${eval_progress.dataset_size} item(s) in your eval dataset. This is generally too small to get a good sense of how well your task run methods perform.`}
              warning_color="warning"
              tight={true}
            />
          </div>
        {/if}
      </div>
    </div>
  {/if}
</AppPage>

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

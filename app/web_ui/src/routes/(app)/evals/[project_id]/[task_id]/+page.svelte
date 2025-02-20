<script lang="ts">
  import AppPage from "../../../app_page.svelte"
  import EmptyEvaluator from "./empty_eval.svelte"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount } from "svelte"
  import { goto } from "$app/navigation"
  import { page } from "$app/stores"
  import { formatDate } from "$lib/utils/formatters"
  import { provider_name_from_id, load_available_models } from "$lib/stores"

  $: project_id = $page.params.project_id
  $: task_id = $page.params.task_id

  let evaluators: Evaluator[] | null = null
  let evaluators_error: KilnError | null = null
  let evaluators_loading = true

  let run_configs: RunConfig[] | null = null
  let run_configs_error: KilnError | null = null
  let run_configs_loading = true

  $: is_empty = !evaluators || evaluators.length == 0

  // TODO use for both loading calls
  $: loading = evaluators_loading || run_configs_loading

  onMount(async () => {
    await load_available_models()
    // Called in parallel
    get_evals()
    get_run_configs()
  })

  async function get_run_configs() {
    run_configs_loading = false
    run_configs = []
  }

  async function get_evals() {
    evaluators_loading = false
    evaluators = []
    return
  }
</script>

<AppPage
  title="Evals"
  subtitle="Evaluate models, prompts, and more."
  sub_subtitle="Read the Docs"
  sub_subtitle_link="https://docs.getkiln.ai/docs/evaluationsTODO"
  action_buttons={is_empty
    ? []
    : [
        {
          label: "Create Evaluator",
          href: `/evals/${project_id}/${task_id}/create_evaluator`,
          primary: true,
        },
      ]}
>
  {#if loading}
    <div class="w-full min-h-[50vh] flex justify-center items-center">
      <div class="loading loading-spinner loading-lg"></div>
    </div>
  {:else if is_empty}
    <div class="flex flex-col items-center justify-center min-h-[60vh]">
      <EmptyEvaluator {project_id} {task_id} />
    </div>
  {:else if evaluators}
    <div class="overflow-x-auto rounded-lg border">
      <table class="table">
        <thead>
          <tr>
            <th> ID </th>
            <th> Name </th>
            <th> Provider</th>
            <th> Base Model</th>
            <th> Created At </th>
          </tr>
        </thead>
        <tbody>
          {#each evaluators as evaluator}
            <tr
              class="hover cursor-pointer"
              on:click={() => {
                goto(
                  `/evals/${project_id}/${task_id}/evaluator/${evaluator.id}`,
                )
              }}
            >
              <td> {evaluator.id} </td>
              <td> {evaluator.name} </td>
              <td> {provider_name_from_id(evaluator.provider)} </td>
              <td> {evaluator.base_model_id} </td>
              <td> {formatDate(evaluator.created_at)} </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if evaluators_error}
    <div
      class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
    >
      <div class="font-medium">Error Loading Evaluators</div>
      <div class="text-error text-sm">
        {evaluators_error.getMessage() || "An unknown error occurred"}
      </div>
    </div>
  {/if}
</AppPage>

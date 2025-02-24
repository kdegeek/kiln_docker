<script lang="ts">
  import AppPage from "../../../../../../../app_page.svelte"
  import type {
    EvalRunResult,
    Eval,
    EvalConfig,
    TaskRunConfig,
  } from "$lib/types"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount, tick } from "svelte"
  import { page } from "$app/stores"
  import { string_to_json_key } from "$lib/utils/json_schema_editor/json_schema_templates"
  import {
    model_info,
    load_model_info,
    model_name,
    provider_name_from_id,
    prompt_name_from_id,
    load_available_prompts,
    load_available_models,
  } from "$lib/stores"

  let results: EvalRunResult | null = null
  let results_error: KilnError | null = null
  let results_loading = true

  onMount(async () => {
    // Wait for params to load
    await tick()
    // Wait for these 3 to load, as they are needed for better labels. Usually already cached and instant.
    await Promise.all([
      load_model_info(),
      load_available_prompts(),
      load_available_models(),
    ])
    get_evals()
  })

  async function get_evals() {
    try {
      results_loading = true
      const { data, error } = await client.GET(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_config/{eval_config_id}/run_config/{run_config_id}/results",
        {
          params: {
            path: {
              project_id: $page.params.project_id,
              task_id: $page.params.task_id,
              eval_id: $page.params.eval_id,
              eval_config_id: $page.params.eval_config_id,
              run_config_id: $page.params.run_config_id,
            },
          },
        },
      )
      if (error) {
        throw error
      }
      results = data
    } catch (error) {
      results_error = createKilnError(error)
    } finally {
      results_loading = false
    }
  }

  function get_run_config_properties(
    run_config: TaskRunConfig | null,
    evaluator: Eval | null,
  ): Record<string, string> {
    if (!run_config || !evaluator) {
      return {}
    }
    return {
      Name: run_config.name,
      Model: model_name(
        run_config.run_config_properties?.model_name,
        $model_info,
      ),
      Provider: provider_name_from_id(
        run_config.run_config_properties?.model_provider_name,
      ),
      Prompt: prompt_name_from_id(run_config.run_config_properties?.prompt_id),
      "Input Source": evaluator.eval_set_filter_id,
    }
  }

  function get_eval_properties(
    evaluator: Eval | null,
    eval_config: EvalConfig | null,
  ): Record<string, string> {
    if (!evaluator || !eval_config) {
      return {}
    }
    return {
      Name: evaluator.name,
      "Eval Config Name": eval_config.name,
      "Eval Type": eval_config.config_type,
      "Eval Model": model_name(
        eval_config.model.properties["model_name"] + "",
        $model_info,
      ),
      "Eval Provider": provider_name_from_id(
        eval_config.model.properties["model_provider"] + "",
      ),
    }
  }
</script>

<AppPage
  title="Eval Results"
  subtitle="Evaluating a task run config, with an evaluator."
>
  {#if results_loading}
    <div class="w-full min-h-[50vh] flex justify-center items-center">
      <div class="loading loading-spinner loading-lg"></div>
    </div>
  {:else if results_error}
    <div
      class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
    >
      <div class="font-medium">Error Loading Eval Results</div>
      <div class="text-error text-sm">
        {results_error.getMessage() || "An unknown error occurred"}
      </div>
    </div>
  {:else if results && results.results.length === 0}
    <div
      class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
    >
      <div class="font-medium">Eval Results Empty</div>
      <div class="text-error text-sm">
        No results found for this run config.
      </div>
    </div>
  {:else if results}
    <div class="flex flex-col xl:flex-row gap-8 xl:gap-16 mb-8">
      <div class="grow basis-1/2">
        <div class="text-xl font-bold">Task Run Config</div>
        <div class="text-sm text-gray-500 mb-4">
          How the outputs were generated.
        </div>
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each Object.entries(get_run_config_properties(results.run_config, results.eval)) as [prop_name, prop_value]}
            <div class="flex items-center">{prop_name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {prop_value}
            </div>
          {/each}
        </div>
      </div>
      <div class="grow basis-1/2">
        <div class="text-xl font-bold">Evaluator</div>
        <div class="text-sm text-gray-500 mb-4">
          How the outputs were evaluated.
        </div>
        <div
          class="grid grid-cols-[auto,1fr] gap-y-2 gap-x-4 text-sm 2xl:text-base"
        >
          {#each Object.entries(get_eval_properties(results.eval, results.eval_config)) as [prop_name, prop_value]}
            <div class="flex items-center">{prop_name}</div>
            <div class="flex items-center text-gray-500 overflow-x-hidden">
              {prop_value}
            </div>
          {/each}
        </div>
      </div>
    </div>
    <div class="overflow-x-auto rounded-lg border">
      <table class="table">
        <thead>
          <tr>
            <th>Input</th>
            <th>Output</th>
            {#each results.eval.output_scores as score}
              <th class="text-center">{score.name}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each results.results as result}
            <tr>
              <td> {result.input} </td>
              <td> {result.output} </td>
              {#each results.eval.output_scores as score}
                {@const score_value =
                  result.scores[string_to_json_key(score.name)]}
                <td class="text-center">
                  {score_value ? score_value.toFixed(2) : "N/A"}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</AppPage>

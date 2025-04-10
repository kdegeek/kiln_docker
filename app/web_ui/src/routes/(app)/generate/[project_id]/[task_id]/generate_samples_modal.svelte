<script lang="ts">
  import type { SampleDataNode } from "./gen_model"
  import AvailableModelsDropdown from "../../../run/available_models_dropdown.svelte"
  import IncrementUi from "./increment_ui.svelte"
  import { KilnError } from "../../../../../lib/utils/error_handlers"
  import { client } from "$lib/api_client"
  import { createKilnError } from "$lib/utils/error_handlers"

  interface TopicNodeWithPath {
    path: string[]
    node: SampleDataNode
  }

  export let id: string
  export let data: SampleDataNode
  export let path: string[]
  export let project_id: string
  export let task_id: string
  export let human_guidance: string | null = null
  export let model: string
  export let num_samples_to_generate: number = 8
  export let custom_topics_string: string | null = null
  export let cascade_mode: boolean = false

  export let on_completed: () => void

  function add_synthetic_samples(
    topic: SampleDataNode,
    samples: unknown[],
    model_name: string,
    model_provider: string,
  ) {
    // Add ignoring dupes and empty strings
    for (const sample of samples) {
      if (!sample) {
        continue
      }
      let input: string | null = null
      if (typeof sample == "string") {
        input = sample
      } else if (typeof sample == "object" || Array.isArray(sample)) {
        input = JSON.stringify(sample)
      }
      if (input) {
        topic.samples.push({
          input: input,
          saved_id: null,
          model_name,
          model_provider,
        })
      }
    }
  }

  let sample_generating: boolean = false
  let sample_generation_error: KilnError | null = null
  async function generate_samples(topic: TopicNodeWithPath) {
    try {
      if (!model) {
        throw new KilnError("No model selected.", null)
      }
      const model_provider = model.split("/")[0]
      const model_name = model.split("/").slice(1).join("/")
      if (!model_name || !model_provider) {
        throw new KilnError("Invalid model selected.", null)
      }
      const { data: generate_response, error: generate_error } =
        await client.POST(
          "/api/projects/{project_id}/tasks/{task_id}/generate_samples",
          {
            body: {
              topic: topic.path,
              num_samples: num_samples_to_generate,
              model_name: model_name,
              provider: model_provider,
              human_guidance: human_guidance ? human_guidance : null, // clear empty string
            },
            params: {
              path: {
                project_id,
                task_id,
              },
            },
          },
        )
      if (generate_error) {
        throw generate_error
      }
      const response = JSON.parse(generate_response.output.output)
      if (
        !response ||
        !response.generated_samples ||
        !Array.isArray(response.generated_samples)
      ) {
        throw new KilnError("No options returned.", null)
      }
      // Add new samples
      add_synthetic_samples(
        topic.node,
        response.generated_samples,
        model_name,
        model_provider,
      )
    } catch (e) {
      // TODO: handle errors better and distinguish between sub-errors and
      // orchestration errors
      if (e instanceof Error && e.message.includes("Load failed")) {
        sample_generation_error = new KilnError(
          "Could not generate samples, unknown error. If it persists, try another model.",
          null,
        )
      } else {
        sample_generation_error = createKilnError(e)
      }
    }
  }

  /**
   * Return all descendant topic nodes in the tree (excluding the node itself).
   */
  function get_descendant_topic_nodes(
    node: TopicNodeWithPath,
  ): TopicNodeWithPath[] {
    const descendants: TopicNodeWithPath[] = []

    const stack: TopicNodeWithPath[] = [node]
    while (stack.length > 0) {
      const curr = stack.pop()!
      descendants.push(curr)

      // add children and construct their paths
      curr.node.sub_topics.forEach((n) => {
        stack.push({
          path: curr.path.concat(n.topic),
          node: n,
        })
      })
    }

    // remove the starting node from the list
    return descendants.slice(1)
  }

  /**
   * Return all leaf topic nodes in the tree (including the node itself if it is a leaf).
   */
  function collect_leaf_topic_nodes(): TopicNodeWithPath[] {
    const node_with_path = { path, node: data }
    return [node_with_path]
      .concat(get_descendant_topic_nodes(node_with_path))
      .filter((t) => t.node.sub_topics.length == 0)
  }

  async function generate_samples_for_all_leaf_nodes() {
    const descendant_leaf_topics = collect_leaf_topic_nodes()
    for (const topic of descendant_leaf_topics) {
      await generate_samples(topic)
    }
  }

  async function generate() {
    sample_generating = true
    sample_generation_error = null

    if (cascade_mode) {
      await generate_samples_for_all_leaf_nodes()
    } else {
      await generate_samples({ path, node: data })
    }

    on_completed()

    sample_generating = false
  }
</script>

<dialog id={`${id}-generate-samples`} class="modal">
  <div class="modal-box">
    <form method="dialog">
      <button
        class="btn btn-sm text-xl btn-circle btn-ghost absolute right-2 top-2 focus:outline-none"
        >✕</button
      >
    </form>
    <h3 class="text-lg font-bold">
      Generate Samples{cascade_mode ? " (cascade)" : ""}
    </h3>
    <p class="text-sm font-light mb-8">
      Add synthetic data samples
      {#if path.length > 0}
        to {path.join(" → ")}
      {/if}
    </p>
    {#if sample_generating}
      <div class="flex flex-row justify-center">
        <div class="loading loading-spinner loading-lg my-12"></div>
      </div>
    {:else}
      <div class="flex flex-col gap-2">
        {#if sample_generation_error}
          <div class="alert alert-error">
            {sample_generation_error.message}
          </div>
        {/if}
        <div class="flex flex-row items-center gap-4 mt-4 mb-2">
          <div class="flex-grow font-medium text-sm">
            Sample Count for each topic
          </div>
          <IncrementUi bind:value={num_samples_to_generate} />
        </div>
        <AvailableModelsDropdown requires_data_gen={true} bind:model />
        <button
          class="btn mt-6 {custom_topics_string ? '' : 'btn-primary'}"
          on:click={generate}
        >
          Generate {num_samples_to_generate} Samples
        </button>
      </div>
    {/if}
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>

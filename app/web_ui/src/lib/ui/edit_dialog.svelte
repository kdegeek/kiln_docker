<script lang="ts">
  import Dialog from "./dialog.svelte"
  import FormContainer from "$lib/utils/form_container.svelte"
  import FormElement from "$lib/utils/form_element.svelte"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { base_url } from "$lib/api_client"

  export let name: string
  export let after_save: () => void = () => {
    // The parent page can override this, but reload the page by default
    window.location.reload()
  }
  export let patch_url: string

  type EditField = {
    label: string
    api_name: string
    value: string
    input_type: "input" | "textarea"
    description?: string
    info_description?: string
    placeholder?: string
    optional?: boolean
    max_length?: number
  }
  export let fields: EditField[]

  let error: KilnError | null = null
  let loading = false

  async function save() {
    loading = true
    try {
      const body = fields.reduce(
        (acc, field) => {
          acc[field.api_name] = field.value
          return acc
        },
        {} as Record<string, string>,
      )
      const response = await fetch(base_url + patch_url, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        let error_body: unknown
        try {
          error_body = await response.json()
        } catch (e) {
          throw new Error("Failed to save edit. Invalid JSON response.")
        }
        throw createKilnError(error_body)
      }
      after_save()
    } catch (e) {
      error = createKilnError(e)
    } finally {
      loading = false
    }
  }

  let dialog: Dialog | null = null
  export function show() {
    dialog?.show()
  }
</script>

<Dialog title={"Edit " + name} bind:this={dialog}>
  <div class="mt-6">
    <FormContainer
      submit_label="Save"
      {error}
      on:submit={save}
      submitting={loading}
    >
      {#each fields as field}
        <FormElement
          bind:value={field.value}
          id={field.api_name}
          label={field.label}
          description={field.description}
          inputType={field.input_type}
          info_description={field.info_description}
          placeholder={field.placeholder}
          optional={field.optional}
          max_length={field.max_length}
        />
      {/each}
    </FormContainer>
  </div>
</Dialog>

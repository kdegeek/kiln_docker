import logging
import time

import vertexai
from google.cloud import storage
from google.cloud.aiplatform_v1beta1 import types as gca_types
from vertexai.tuning import sft

from kiln_ai.adapters.fine_tune.base_finetune import (
    BaseFinetuneAdapter,
    FineTuneParameter,
    FineTuneStatus,
    FineTuneStatusType,
)
from kiln_ai.adapters.fine_tune.dataset_formatter import DatasetFormat, DatasetFormatter
from kiln_ai.datamodel import DatasetSplit, StructuredOutputMode, Task
from kiln_ai.utils.config import Config

logger = logging.getLogger(__name__)


class VertexFinetune(BaseFinetuneAdapter):
    """
    A fine-tuning adapter for Vertex AI.
    """

    async def status(self) -> FineTuneStatus:
        """
        Get the status of the fine-tune.
        """

        # Update the datamodel with the latest status if it has changed
        status = await self._status()
        if status.status != self.datamodel.latest_status:
            self.datamodel.latest_status = status.status
            if self.datamodel.path:
                self.datamodel.save_to_file()
        return status

    async def _status(self) -> FineTuneStatus:
        if not self.datamodel or not self.datamodel.provider_id:
            return FineTuneStatus(
                status=FineTuneStatusType.pending,
                message="This fine-tune has not been started or has not been assigned a provider ID.",
            )

        response = sft.SupervisedTuningJob(
            self.datamodel.provider_id
            # f"projects/{project}/locations/{location}/tuningJobs/{tune_job_id}"
        )
        # If the fine-tuned model ID has been updated, update the datamodel
        try:
            if self.datamodel.fine_tune_model_id != response.tuned_model_endpoint_name:
                self.datamodel.fine_tune_model_id = response.tuned_model_endpoint_name
                self.datamodel.save_to_file()
        except Exception:
            # Don't let this error crash the status call
            pass

        error = response.error
        if error and error.code != 0:
            return FineTuneStatus(
                status=FineTuneStatusType.failed,
                message=f"Fine Tune Job Error: {error.message} [{error.code}]",
            )
        state = response.state
        if state in [
            gca_types.JobState.JOB_STATE_FAILED,
            gca_types.JobState.JOB_STATE_EXPIRED,
        ]:
            return FineTuneStatus(
                status=FineTuneStatusType.failed,
                message="Fine Tune Job Failed",
            )
        if state in [
            gca_types.JobState.JOB_STATE_CANCELLED,
            gca_types.JobState.JOB_STATE_CANCELLING,
        ]:
            return FineTuneStatus(
                status=FineTuneStatusType.failed, message="Fine Tune Job Cancelled"
            )
        if state in [
            gca_types.JobState.JOB_STATE_QUEUED,
            gca_types.JobState.JOB_STATE_PENDING,
            gca_types.JobState.JOB_STATE_RUNNING,
        ]:
            return FineTuneStatus(
                status=FineTuneStatusType.running,
                message="Fine tune job is running.",
            )
        if state in [
            gca_types.JobState.JOB_STATE_SUCCEEDED,
            gca_types.JobState.JOB_STATE_PARTIALLY_SUCCEEDED,
        ]:
            return FineTuneStatus(
                status=FineTuneStatusType.completed, message="Fine tune job completed"
            )

        if state not in [
            gca_types.JobState.JOB_STATE_UPDATING,
            gca_types.JobState.JOB_STATE_UNSPECIFIED,
            gca_types.JobState.JOB_STATE_PAUSED,
        ]:
            # While the above states map to "unknown", they are expected unknowns. Log if some new state appears we aren't expecting
            logger.warning(f"Unknown Vertex AI Finetune status: [{state}]")

        return FineTuneStatus(
            status=FineTuneStatusType.unknown, message=f"Unknown state: [{state}]"
        )

    async def _start(self, dataset: DatasetSplit) -> None:
        task = self.datamodel.parent_task()
        if not task:
            raise ValueError("Task is required to start a fine-tune")

        # Use chat format for unstructured output, and JSON for formatted output (was previously function calls)
        format = DatasetFormat.VERTEX_GEMINI_1_5
        if task.output_json_schema:
            # TODO: check modes
            self.datamodel.structured_output_mode = StructuredOutputMode.json_mode
        train_file_id = await self.generate_and_upload_jsonl(
            dataset, self.datamodel.train_split_name, task, format
        )
        validation_file_id = None
        if self.datamodel.validation_split_name:
            validation_file_id = await self.generate_and_upload_jsonl(
                dataset, self.datamodel.validation_split_name, task, format
            )

        # Filter to hyperparameters which are set via the hyperparameters field (some like seed are set via the API)
        hyperparameters = {
            k: v
            for k, v in self.datamodel.parameters.items()
            if k in ["epochs", "learning_rate_multiplier", "adapter_size"]
        }

        project = Config.shared().vertex_project_id
        location = Config.shared().vertex_location
        vertexai.init(project=project, location=location)

        sft_tuning_job = sft.train(
            source_model=self.datamodel.base_model_id,
            train_dataset=train_file_id,
            validation_dataset=validation_file_id,
            tuned_model_display_name=f"kiln_finetune_{self.datamodel.id}",
            # Advanced use only below. It is recommended to use auto-selection and leave them unset
            epochs=1,
            adapter_size=4,
            # learning_rate_multiplier=1.0,
            labels={
                "source": "kiln",
                "kiln_finetune_id": str(self.datamodel.id),
                "kiln_task_id": str(task.id),
            },
            # TODO set real hyperparameters
        )
        print(sft_tuning_job)
        self.datamodel.provider_id = sft_tuning_job.resource_name
        # self.datamodel.fine_tune_model_id = ft.fine_tuned_model

        return None

    async def generate_and_upload_jsonl(
        self, dataset: DatasetSplit, split_name: str, task: Task, format: DatasetFormat
    ) -> str:
        formatter = DatasetFormatter(
            dataset, self.datamodel.system_message, self.datamodel.thinking_instructions
        )
        path = formatter.dump_to_file(split_name, format, self.datamodel.data_strategy)

        project = Config.shared().vertex_project_id
        location = Config.shared().vertex_location
        storage_client = storage.Client(project=project)

        bucket_name = "kiln-ai-data"

        # Check if bucket exists and create it if it doesn't
        if not storage_client.lookup_bucket(bucket_name):
            bucket = storage_client.create_bucket(bucket_name, location=location)
        else:
            bucket = storage_client.bucket(bucket_name)

        # Create a blob and upload
        epoch_timestamp = int(time.time())
        blob_name = f"{epoch_timestamp}/{path.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(path)

        print(f"File uploaded to gs://{bucket.name}/{blob.name}")
        return f"gs://{bucket.name}/{blob.name}"

    @classmethod
    def available_parameters(cls) -> list[FineTuneParameter]:
        return [
            FineTuneParameter(
                name="learning_rate_multiplier",
                type="float",
                description="Scaling factor for the learning rate. A smaller learning rate may be useful to avoid overfitting. Defaults to 1.0 (don't scale vertex's learning rate).",
                optional=True,
            ),
            FineTuneParameter(
                name="epochs",
                type="int",
                description="The number of epochs to train the model for. An epoch refers to one full cycle through the training dataset. Defaults to 'auto'",
                optional=True,
            ),
            FineTuneParameter(
                name="adapter_size",
                type="int",
                description="The size of the adapter to use for the fine-tune (Lora Rank). One of 1, 4, 8, or 16. By default Vertex will auto-select a size.",
                optional=True,
            ),
        ]

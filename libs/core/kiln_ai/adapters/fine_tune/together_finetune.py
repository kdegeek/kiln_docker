from typing import Literal, Tuple

from together import Together
from together.types.files import FilePurpose
from together.types.finetune import FinetuneJobStatus as TogetherFinetuneJobStatus

from kiln_ai.adapters.fine_tune.base_finetune import (
    BaseFinetuneAdapter,
    FineTuneParameter,
    FineTuneStatus,
    FineTuneStatusType,
)
from kiln_ai.adapters.fine_tune.dataset_formatter import DatasetFormat, DatasetFormatter
from kiln_ai.datamodel import DatasetSplit, StructuredOutputMode, Task
from kiln_ai.datamodel import Finetune as FinetuneModel
from kiln_ai.utils.config import Config

_pending_statuses = [
    TogetherFinetuneJobStatus.STATUS_PENDING,
    TogetherFinetuneJobStatus.STATUS_QUEUED,
]
_running_statuses = [
    TogetherFinetuneJobStatus.STATUS_RUNNING,
    TogetherFinetuneJobStatus.STATUS_COMPRESSING,
    TogetherFinetuneJobStatus.STATUS_UPLOADING,
]
_completed_statuses = [TogetherFinetuneJobStatus.STATUS_COMPLETED]
_failed_statuses = [
    TogetherFinetuneJobStatus.STATUS_CANCELLED,
    TogetherFinetuneJobStatus.STATUS_CANCEL_REQUESTED,
    TogetherFinetuneJobStatus.STATUS_ERROR,
    TogetherFinetuneJobStatus.STATUS_USER_ERROR,
]


class TogetherFinetune(BaseFinetuneAdapter):
    """
    A fine-tuning adapter for Together.ai.
    """

    def __init__(self, datamodel: FinetuneModel):
        super().__init__(datamodel)
        api_key = Config.shared().together_api_key
        if not api_key:
            raise ValueError("Together.ai API key not set")
        self.client = Together(api_key=api_key)

    async def status(self) -> FineTuneStatus:
        status, _ = await self._status()
        # update the datamodel if the status has changed
        if self.datamodel.latest_status != status.status:
            self.datamodel.latest_status = status.status
            if self.datamodel.path:
                self.datamodel.save_to_file()
        return status

    async def _status(self) -> Tuple[FineTuneStatus, str | None]:
        try:
            fine_tuning_job_id = self.datamodel.provider_id
            if not fine_tuning_job_id:
                return FineTuneStatus(
                    status=FineTuneStatusType.unknown,
                    message="Fine-tuning job ID not set. Can not retrieve status.",
                ), None

            # retrieve the fine-tuning job
            together_finetune = self.client.fine_tuning.retrieve(id=fine_tuning_job_id)

            status = together_finetune.status
            if status in _pending_statuses:
                return FineTuneStatus(
                    status=FineTuneStatusType.pending,
                    message=f"Fine-tuning job is pending [{status}]",
                ), fine_tuning_job_id
            elif status in _running_statuses:
                return FineTuneStatus(
                    status=FineTuneStatusType.running,
                    message=f"Fine-tuning job is running [{status}]",
                ), fine_tuning_job_id
            elif status in _completed_statuses:
                return FineTuneStatus(
                    status=FineTuneStatusType.completed,
                    message="Fine-tuning job completed",
                ), fine_tuning_job_id
            elif status in _failed_statuses:
                return FineTuneStatus(
                    status=FineTuneStatusType.failed,
                    message=f"Fine-tuning job failed [{status}]",
                ), fine_tuning_job_id
            else:
                return FineTuneStatus(
                    status=FineTuneStatusType.unknown,
                    message=f"Unknown fine-tuning job status [{status}]",
                ), fine_tuning_job_id
        except Exception as e:
            return FineTuneStatus(
                status=FineTuneStatusType.unknown,
                message=f"Error retrieving fine-tuning job status: {e}",
            ), None

    async def _start(self, dataset: DatasetSplit) -> None:
        task = self.datamodel.parent_task()
        if not task:
            raise ValueError("Task is required to start a fine-tune")

        # TODO: check if these are the correct formats
        format = DatasetFormat.OPENAI_CHAT_JSONL
        if task.output_json_schema:
            # This formatter will check it's valid JSON, and normalize the output (chat format just uses exact string).
            format = DatasetFormat.OPENAI_CHAT_JSON_SCHEMA_JSONL
            # TODO P0 - fix this. it should work
            # Since we're training with JSON string output, we'll use json mode at call time
            self.datamodel.structured_output_mode = (
                StructuredOutputMode.json_instructions
            )

        train_file_id = await self.generate_and_upload_jsonl(
            dataset, self.datamodel.train_split_name, task, format
        )

        # Max 40 characters, helps id the fine-tune job
        display_name = f"kiln_ai_{self.datamodel.id}"[:40]

        # TODO P0: don't hardcode these
        parameters = self.datamodel.parameters
        together_finetune = self.client.fine_tuning.create(
            training_file=train_file_id,
            model=self.datamodel.base_model_id,
            n_epochs=self.epochs(),
            learning_rate=self.learning_rate(),
            batch_size=self.batch_size(),
            n_checkpoints=self.num_checkpoints(),
            suffix=display_name,
        )

        # 2 different IDs, output_name is the name of the model that results from the fine-tune job, the finetune_job_id is the ID of the fine-tune job
        self.datamodel.provider_id = together_finetune.id
        self.datamodel.fine_tune_model_id = together_finetune.output_name

        if self.datamodel.path:
            self.datamodel.save_to_file()

    def epochs(self) -> int:
        parameters = self.datamodel.parameters
        if "epochs" in parameters and isinstance(parameters["epochs"], int):
            return parameters["epochs"]
        return 1

    def learning_rate(self) -> float:
        parameters = self.datamodel.parameters
        if "learning_rate" in parameters and isinstance(
            parameters["learning_rate"], float
        ):
            return parameters["learning_rate"]
        return 1e-5

    def num_checkpoints(self) -> int:
        parameters = self.datamodel.parameters
        if "num_checkpoints" in parameters and isinstance(
            parameters["num_checkpoints"], int
        ):
            return parameters["num_checkpoints"]
        return 1

    def batch_size(self) -> int | Literal["max"]:
        parameters = self.datamodel.parameters
        if "batch_size" in parameters and isinstance(parameters["batch_size"], int):
            return parameters["batch_size"]
        return "max"

    async def generate_and_upload_jsonl(
        self, dataset: DatasetSplit, split_name: str, task: Task, format: DatasetFormat
    ) -> str:
        formatter = DatasetFormatter(
            dataset=dataset,
            system_message=self.datamodel.system_message,
            thinking_instructions=self.datamodel.thinking_instructions,
        )
        path = formatter.dump_to_file(split_name, format, self.datamodel.data_strategy)

        try:
            together_file = self.client.files.upload(
                file=path,
                purpose=FilePurpose.FineTune,
                check=True,
            )
            return together_file.id
        except Exception as e:
            raise ValueError(f"Failed to upload dataset: {e}")

    @classmethod
    def available_parameters(cls) -> list[FineTuneParameter]:
        return [
            FineTuneParameter(
                name="epochs",
                description="The number of epochs to fine-tune for. If not provided, defaults to 1.",
                type="int",
                optional=True,
            ),
            FineTuneParameter(
                name="learning_rate",
                description="The learning rate to use for fine-tuning. If not provided, defaults to 0.00001",
                type="float",
                optional=True,
            ),
            FineTuneParameter(
                name="batch_size",
                description="The batch size of dataset used in training can be configured with a positive integer less than 1024 and in power of 2. If not specified, defaults to the max supported value for this model.",
                type="int",
                optional=True,
            ),
            FineTuneParameter(
                name="num_checkpoints",
                description="The number of checkpoints to save during training. If not specified, defaults to 1.",
                type="int",
                optional=True,
            ),
        ]

    async def _deploy(self) -> bool:
        # Together is awesome. Auto deploys!
        # If I add support for non-Lora serverless I'll have to modify this, but good for now.
        return True

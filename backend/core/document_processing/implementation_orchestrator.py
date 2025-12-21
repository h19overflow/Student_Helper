"""
SQS → Lambda Implementation Orchestrator

Interactive CLI tool to guide through 6-stage implementation:
1. SQS Event Schema
2. Lambda Handler
3. Pipeline Integration
4. Database Updates
5. Error Handling & DLQ
6. Testing & Deployment

Usage:
    python -m backend.core.document_processing.implementation_orchestrator

System role: Implementation workflow orchestrator
"""

import os
import sys
import json
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class Stage(Enum):
    """Implementation stages."""

    SCHEMA = 1
    HANDLER = 2
    PIPELINE = 3
    DATABASE = 4
    ERROR_HANDLING = 5
    TESTING = 6


class ImplementationStep:
    """Single implementation step with checklist."""

    def __init__(
        self,
        stage: Stage,
        title: str,
        description: str,
        files_to_create: List[str],
        files_to_update: List[str],
        test_command: str,
        doc_reference: str,
    ) -> None:
        """
        Initialize implementation step.

        Args:
            stage: Implementation stage
            title: Step title
            description: What this step does
            files_to_create: Files to create in this step
            files_to_update: Files to modify in this step
            test_command: Command to run tests
            doc_reference: Path to documentation file
        """
        self.stage = stage
        self.title = title
        self.description = description
        self.files_to_create = files_to_create
        self.files_to_update = files_to_update
        self.test_command = test_command
        self.doc_reference = doc_reference
        self.completed = False

    def display(self) -> None:
        """Display step information."""
        print(f"\n{'='*70}")
        print(f"Stage {self.stage.value}: {self.title}")
        print(f"{'='*70}")
        print(f"\n{self.description}\n")

        if self.files_to_create:
            print("📁 Files to Create:")
            for file in self.files_to_create:
                print(f"   - {file}")

        if self.files_to_update:
            print("\n✏️  Files to Update:")
            for file in self.files_to_update:
                print(f"   - {file}")

        print(f"\n📖 Documentation: {self.doc_reference}")
        print(f"\n🧪 Test Command: {self.test_command}\n")


class ImplementationOrchestrator:
    """Orchestrate 6-stage SQS Lambda implementation."""

    def __init__(self) -> None:
        """Initialize orchestrator."""
        self.stages: Dict[Stage, ImplementationStep] = self._init_stages()
        self.current_stage = Stage.SCHEMA
        self.state_file = Path(".implementation_state.json")
        self.load_state()

    def _init_stages(self) -> Dict[Stage, ImplementationStep]:
        """Initialize all stages with their details."""
        doc_base = "documentation/06_sqs_lambda_implementation"

        return {
            Stage.SCHEMA: ImplementationStep(
                stage=Stage.SCHEMA,
                title="SQS Event Schema",
                description=(
                    "Define Pydantic schema that validates SQS messages.\n"
                    "This stage defines the contract between API and Lambda."
                ),
                files_to_create=[
                    "backend/core/document_processing/models/sqs_event.py",
                    "backend/core/document_processing/tests/test_sqs_event.py",
                ],
                files_to_update=["backend/core/document_processing/models/__init__.py"],
                test_command="pytest backend/core/document_processing/tests/test_sqs_event.py -v",
                doc_reference=f"{doc_base}/STAGE_1_SQS_EVENT_SCHEMA.md",
            ),
            Stage.HANDLER: ImplementationStep(
                stage=Stage.HANDLER,
                title="Lambda Handler Setup",
                description=(
                    "Implement Lambda handler to parse SQS messages,\n"
                    "validate environment, and handle errors gracefully."
                ),
                files_to_create=[
                    "backend/core/document_processing/tests/test_lambda_handler.py",
                ],
                files_to_update=[
                    "backend/core/document_processing/lambda_handler.py",
                ],
                test_command="pytest backend/core/document_processing/tests/test_lambda_handler.py -v",
                doc_reference=f"{doc_base}/STAGE_2_LAMBDA_HANDLER.md",
            ),
            Stage.PIPELINE: ImplementationStep(
                stage=Stage.PIPELINE,
                title="Pipeline Integration",
                description=(
                    "Connect Lambda handler to existing DocumentPipeline.\n"
                    "This is where the actual document processing happens."
                ),
                files_to_create=[
                    "backend/core/document_processing/tests/test_pipeline_integration.py",
                ],
                files_to_update=[
                    "backend/core/document_processing/lambda_handler.py",
                ],
                test_command="pytest backend/core/document_processing/tests/test_pipeline_integration.py -v",
                doc_reference=f"{doc_base}/STAGE_3_PIPELINE_INTEGRATION.md",
            ),
            Stage.DATABASE: ImplementationStep(
                stage=Stage.DATABASE,
                title="Database Status Updates",
                description=(
                    "Update RDS document status as processing progresses.\n"
                    "PENDING → PROCESSING → COMPLETED/FAILED"
                ),
                files_to_create=[
                    "backend/core/document_processing/database/document_status_updater.py",
                    "backend/core/document_processing/tests/test_database_updater.py",
                ],
                files_to_update=[
                    "backend/core/document_processing/lambda_handler.py",
                    "backend/core/document_processing/database/__init__.py",
                ],
                test_command="pytest backend/core/document_processing/tests/test_database_updater.py -v",
                doc_reference=f"{doc_base}/STAGE_4_DATABASE_UPDATES.md",
            ),
            Stage.ERROR_HANDLING: ImplementationStep(
                stage=Stage.ERROR_HANDLING,
                title="Error Handling & DLQ",
                description=(
                    "Implement Dead Letter Queue for failed messages.\n"
                    "Add structured error logging for observability."
                ),
                files_to_create=[
                    "backend/core/document_processing/error_handling/error_logger.py",
                    "backend/core/document_processing/error_handling/dlq_handler.py",
                    "backend/core/document_processing/tests/test_error_handling.py",
                ],
                files_to_update=[
                    "backend/core/document_processing/error_handling/__init__.py",
                ],
                test_command="pytest backend/core/document_processing/tests/test_error_handling.py -v",
                doc_reference=f"{doc_base}/STAGE_5_ERROR_HANDLING_DLQ.md",
            ),
            Stage.TESTING: ImplementationStep(
                stage=Stage.TESTING,
                title="Testing & Deployment",
                description=(
                    "Write integration tests for the full flow.\n"
                    "Deploy to AWS and verify end-to-end."
                ),
                files_to_create=[
                    "backend/core/document_processing/tests/test_integration_full_flow.py",
                ],
                files_to_update=[],
                test_command="pytest backend/core/document_processing/tests/test_integration_full_flow.py -v",
                doc_reference=f"{doc_base}/STAGE_6_TESTING_DEPLOYMENT.md",
            ),
        }

    def load_state(self) -> None:
        """Load implementation state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.current_stage = Stage(state.get("current_stage", 1))
                    completed = state.get("completed_stages", [])
                    for stage_num in completed:
                        self.stages[Stage(stage_num)].completed = True
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def save_state(self) -> None:
        """Save implementation state to file."""
        state = {
            "current_stage": self.current_stage.value,
            "completed_stages": [
                s.value for s in self.stages.values() if s.completed
            ],
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def display_menu(self) -> None:
        """Display main menu."""
        print("\n" + "=" * 70)
        print("SQS → Lambda Implementation Orchestrator")
        print("=" * 70)
        print("\nAvailable Commands:\n")

        for stage in Stage:
            status = "✅" if self.stages[stage].completed else "⭕"
            print(f"  {status} {stage.value}. {self.stages[stage].title}")

        print("\n  📋 all     - View all stages")
        print("  📖 docs    - Open documentation")
        print("  🧪 test    - Run tests for current stage")
        print("  📊 status  - Show implementation status")
        print("  ✅ complete - Mark stage as complete")
        print("  🚀 deploy  - Show deployment guide")
        print("  ❌ quit    - Exit\n")

    def handle_stage_command(self, stage_num: str) -> None:
        """Handle stage selection command."""
        try:
            stage = Stage(int(stage_num))
            self.current_stage = stage
            step = self.stages[stage]

            step.display()

            print("Next Steps:")
            print(f"  1. Open documentation: {step.doc_reference}")
            print(f"  2. Create/update files as specified")
            print(f"  3. Run tests: {step.test_command}")
            print(f"  4. Type 'complete' to mark stage complete")

        except (ValueError, KeyError):
            print(f"Invalid stage: {stage_num}")

    def view_all_stages(self) -> None:
        """Display all stages at once."""
        print("\n" + "=" * 70)
        print("All Implementation Stages")
        print("=" * 70)

        for stage in Stage:
            step = self.stages[stage]
            status = "✅ COMPLETED" if step.completed else "⭕ PENDING"
            print(f"\n{status}: Stage {stage.value} - {step.title}")
            print(f"  {step.description}")

    def run_tests(self) -> None:
        """Run tests for current stage."""
        step = self.stages[self.current_stage]
        print(f"\n🧪 Running tests for Stage {self.current_stage.value}...\n")

        try:
            result = subprocess.run(
                step.test_command.split(),
                cwd=Path.cwd(),
                capture_output=False,
            )
            if result.returncode == 0:
                print("\n✅ All tests passed!")
            else:
                print("\n❌ Some tests failed. Check output above.")
        except Exception as e:
            print(f"❌ Error running tests: {e}")

    def mark_complete(self) -> None:
        """Mark current stage as complete."""
        self.stages[self.current_stage].completed = True
        self.save_state()

        print(f"\n✅ Stage {self.current_stage.value} marked as complete!")

        # Move to next stage
        next_stage_num = self.current_stage.value + 1
        if next_stage_num <= len(Stage):
            next_stage = Stage(next_stage_num)
            print(f"\n➡️  Ready for Stage {next_stage_num}: {self.stages[next_stage].title}")
            self.current_stage = next_stage
            self.save_state()

    def show_status(self) -> None:
        """Show implementation progress."""
        completed = sum(1 for s in self.stages.values() if s.completed)
        total = len(self.stages)

        print("\n" + "=" * 70)
        print("Implementation Progress")
        print("=" * 70)
        print(f"\nProgress: {completed}/{total} stages completed\n")

        for stage in Stage:
            step = self.stages[stage]
            status = "✅" if step.completed else "⭕"
            marker = "→ " if stage == self.current_stage else "  "
            print(f"{marker}{status} Stage {stage.value}: {step.title}")

        completion_pct = (completed / total) * 100
        print(f"\nCompletion: {completion_pct:.0f}%")

    def show_deployment_guide(self) -> None:
        """Show deployment guide."""
        print("\n" + "=" * 70)
        print("Deployment Guide")
        print("=" * 70)

        print("""
1. Environment Variables (set before deployment):

   export DOCUMENTS_BUCKET=your-bucket
   export VECTORS_BUCKET=vectors-bucket
   export DATABASE_URL=postgresql://...
   export AWS_REGION=us-east-1

2. Deploy Infrastructure:

   terraform apply -target=aws_sqs_queue.document_processing_queue
   terraform apply -target=aws_sqs_queue.document_processing_dlq
   terraform apply -target=aws_lambda_event_source_mapping

3. Deploy Lambda:

   serverless deploy function -f documentProcessing -s prod

4. Verify Deployment:

   aws sqs get-queue-url --queue-name document-processing-queue
   aws lambda list-event-source-mappings --function-name document-processing

5. Test End-to-End:

   # Upload document via API
   # Check RDS for PENDING status
   # Wait for Lambda to process
   # Verify COMPLETED status

For detailed steps, see: documentation/06_sqs_lambda_implementation/STAGE_6_TESTING_DEPLOYMENT.md
        """)

    def run(self) -> None:
        """Run interactive orchestrator."""
        print("\n🚀 SQS → Lambda Implementation Orchestrator")
        print("Chunk-sized phases for guided implementation\n")

        while True:
            self.display_menu()

            command = input("Enter command (1-6, all, docs, test, status, complete, deploy, quit): ").strip().lower()

            if command == "quit":
                print("\n👋 Goodbye!")
                break
            elif command in ["1", "2", "3", "4", "5", "6"]:
                self.handle_stage_command(command)
            elif command == "all":
                self.view_all_stages()
            elif command == "docs":
                step = self.stages[self.current_stage]
                print(f"\n📖 Opening: {step.doc_reference}")
                print("(Open this file in your editor)")
            elif command == "test":
                self.run_tests()
            elif command == "status":
                self.show_status()
            elif command == "complete":
                self.mark_complete()
            elif command == "deploy":
                self.show_deployment_guide()
            else:
                print(f"❌ Unknown command: {command}")


def main() -> None:
    """Entry point."""
    orchestrator = ImplementationOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()

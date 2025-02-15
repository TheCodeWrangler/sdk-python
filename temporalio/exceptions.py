"""Common Temporal exceptions.

# Temporal Failure

Most Temporal SDKs have a base class that the other Failures extend.
In python, it is the ``FailureError``.

# Application Failure

Workflow, and Activity, and Nexus Operation code use Application Failures to
communicate application-specific failures that happen.
This is the only type of Temporal Failure created and thrown by user code.
In the Python SDK, it is the ``ApplicationError``.

# References

More information can be found in the docs at
https://docs.temporal.io/references/failures#workflow-execution-failures.
"""

import asyncio
from datetime import timedelta
from enum import IntEnum
from typing import Any, Optional, Sequence, Tuple

import temporalio.api.common.v1
import temporalio.api.enums.v1
import temporalio.api.failure.v1


class TemporalError(Exception):
    """Base for all Temporal exceptions."""

    @property
    def cause(self) -> Optional[BaseException]:
        """Cause of the exception.

        This is the same as ``Exception.__cause__``.
        """
        return self.__cause__


class FailureError(TemporalError):
    """Base class for exceptions that cause a workflow execution failure.

    Do not raise this directly: raise ``ApplicationError`` instead.

    Workflow execution failure puts the workflow execution into "Failed" state,
    and no further attempts will be made to progress the workflow execution.

    By default, any exception that does not inherit from this class causes the
    workflow task to be retried, rather than failing the workflow execution. The
    default behavior can be changed by providing a list of exception types to
    ``workflow_failure_exception_types`` when creating a worker or
    ``failure_exception_types`` on the ``@workflow.defn`` decorator.
    """

    def __init__(
        self,
        message: str,
        *,
        failure: Optional[temporalio.api.failure.v1.Failure] = None,
        exc_args: Optional[Tuple] = None,
    ) -> None:
        """Initialize a failure error."""
        if exc_args is None:
            exc_args = (message,)
        super().__init__(*exc_args)
        self._message = message
        self._failure = failure

    @property
    def message(self) -> str:
        """Message."""
        return self._message

    @property
    def failure(self) -> Optional[temporalio.api.failure.v1.Failure]:
        """Underlying protobuf failure object."""
        return self._failure


class WorkflowAlreadyStartedError(FailureError):
    """Thrown by a client or workflow when a workflow execution has already started.

    Attributes:
        workflow_id: ID of the already-started workflow.
        workflow_type: Workflow type name of the already-started workflow.
        run_id: Run ID of the already-started workflow if this was raised by the
            client.
    """

    def __init__(
        self, workflow_id: str, workflow_type: str, *, run_id: Optional[str] = None
    ) -> None:
        """Initialize a workflow already started error."""
        super().__init__("Workflow execution already started")
        self.workflow_id = workflow_id
        self.workflow_type = workflow_type
        self.run_id = run_id


class ApplicationError(FailureError):
    """Raised in workflow/activity code to cause a workflow execution failure.

    Workflow execution failure puts the workflow execution into "Failed" state,
    and no further attempts will be made to progress the workflow execution.

    .. code-block:: python

        from temporalio.exceptions import ApplicationError
        # ...
        if is_delivery and distance.get_kilometers() > 25:
            raise ApplicationError("Customer lives outside the service area")
    """

    def __init__(
        self,
        message: str,
        *details: Any,
        type: Optional[str] = None,
        non_retryable: bool = False,
        next_retry_delay: Optional[timedelta] = None,
    ) -> None:
        """Initialize an application error."""
        super().__init__(
            message,
            # If there is a type, prepend it to the message on the string repr
            exc_args=(message if not type else f"{type}: {message}",),
        )
        self._details = details
        self._type = type
        self._non_retryable = non_retryable
        self._next_retry_delay = next_retry_delay

    @property
    def details(self) -> Sequence[Any]:
        """User-defined details on the error."""
        return self._details

    @property
    def type(self) -> Optional[str]:
        """General error type."""
        return self._type

    @property
    def non_retryable(self) -> bool:
        """Whether the error was set as non-retryable when created.

        Note: This is not whether the error is non-retryable via other means
        such as retry policy. This is just whether the error was marked
        non-retryable upon creation by the user.
        """
        return self._non_retryable

    @property
    def next_retry_delay(self) -> Optional[timedelta]:
        """Delay before the next activity retry attempt.

        User activity code may set this when raising ApplicationError to specify
        a delay before the next activity retry.
        """
        return self._next_retry_delay


class CancelledError(FailureError):
    """Error raised on workflow/activity cancellation."""

    def __init__(self, message: str = "Cancelled", *details: Any) -> None:
        """Initialize a cancelled error."""
        super().__init__(message)
        self._details = details

    @property
    def details(self) -> Sequence[Any]:
        """User-defined details on the error."""
        return self._details


class TerminatedError(FailureError):
    """Error raised on workflow cancellation."""

    def __init__(self, message: str, *details: Any) -> None:
        """Initialize a terminated error."""
        super().__init__(message)
        self._details = details

    @property
    def details(self) -> Sequence[Any]:
        """User-defined details on the error."""
        return self._details


class TimeoutType(IntEnum):
    """Type of timeout for :py:class:`TimeoutError`."""

    START_TO_CLOSE = int(
        temporalio.api.enums.v1.TimeoutType.TIMEOUT_TYPE_START_TO_CLOSE
    )
    SCHEDULE_TO_START = int(
        temporalio.api.enums.v1.TimeoutType.TIMEOUT_TYPE_SCHEDULE_TO_START
    )
    SCHEDULE_TO_CLOSE = int(
        temporalio.api.enums.v1.TimeoutType.TIMEOUT_TYPE_SCHEDULE_TO_CLOSE
    )
    HEARTBEAT = int(temporalio.api.enums.v1.TimeoutType.TIMEOUT_TYPE_HEARTBEAT)


class TimeoutError(FailureError):
    """Error raised on workflow/activity timeout."""

    def __init__(
        self,
        message: str,
        *,
        type: Optional[TimeoutType],
        last_heartbeat_details: Sequence[Any],
    ) -> None:
        """Initialize a timeout error."""
        super().__init__(message)
        self._type = type
        self._last_heartbeat_details = last_heartbeat_details

    @property
    def type(self) -> Optional[TimeoutType]:
        """Type of timeout error."""
        return self._type

    @property
    def last_heartbeat_details(self) -> Sequence[Any]:
        """Last heartbeat details if this is for an activity heartbeat."""
        return self._last_heartbeat_details


class ServerError(FailureError):
    """Error originating in the Temporal server."""

    def __init__(self, message: str, *, non_retryable: bool = False) -> None:
        """Initialize a server error."""
        super().__init__(message)
        self._non_retryable = non_retryable

    @property
    def non_retryable(self) -> bool:
        """Whether this error is non-retryable."""
        return self._non_retryable


class RetryState(IntEnum):
    """Current retry state of the workflow/activity during error."""

    IN_PROGRESS = int(temporalio.api.enums.v1.RetryState.RETRY_STATE_IN_PROGRESS)
    NON_RETRYABLE_FAILURE = int(
        temporalio.api.enums.v1.RetryState.RETRY_STATE_NON_RETRYABLE_FAILURE
    )
    TIMEOUT = int(temporalio.api.enums.v1.RetryState.RETRY_STATE_TIMEOUT)
    MAXIMUM_ATTEMPTS_REACHED = int(
        temporalio.api.enums.v1.RetryState.RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED
    )
    RETRY_POLICY_NOT_SET = int(
        temporalio.api.enums.v1.RetryState.RETRY_STATE_RETRY_POLICY_NOT_SET
    )
    INTERNAL_SERVER_ERROR = int(
        temporalio.api.enums.v1.RetryState.RETRY_STATE_INTERNAL_SERVER_ERROR
    )
    CANCEL_REQUESTED = int(
        temporalio.api.enums.v1.RetryState.RETRY_STATE_CANCEL_REQUESTED
    )


class ActivityError(FailureError):
    """Error raised on activity failure."""

    def __init__(
        self,
        message: str,
        *,
        scheduled_event_id: int,
        started_event_id: int,
        identity: str,
        activity_type: str,
        activity_id: str,
        retry_state: Optional[RetryState],
    ) -> None:
        """Initialize an activity error."""
        super().__init__(message)
        self._scheduled_event_id = scheduled_event_id
        self._started_event_id = started_event_id
        self._identity = identity
        self._activity_type = activity_type
        self._activity_id = activity_id
        self._retry_state = retry_state

    @property
    def scheduled_event_id(self) -> int:
        """Scheduled event ID for this error."""
        return self._scheduled_event_id

    @property
    def started_event_id(self) -> int:
        """Started event ID for this error."""
        return self._started_event_id

    @property
    def identity(self) -> str:
        """Identity for this error."""
        return self._identity

    @property
    def activity_type(self) -> str:
        """Activity type for this error."""
        return self._activity_type

    @property
    def activity_id(self) -> str:
        """Activity ID for this error."""
        return self._activity_id

    @property
    def retry_state(self) -> Optional[RetryState]:
        """Retry state for this error."""
        return self._retry_state


class ChildWorkflowError(FailureError):
    """Error raised on child workflow failure."""

    def __init__(
        self,
        message: str,
        *,
        namespace: str,
        workflow_id: str,
        run_id: str,
        workflow_type: str,
        initiated_event_id: int,
        started_event_id: int,
        retry_state: Optional[RetryState],
    ) -> None:
        """Initialize a child workflow error."""
        super().__init__(message)
        self._namespace = namespace
        self._workflow_id = workflow_id
        self._run_id = run_id
        self._workflow_type = workflow_type
        self._initiated_event_id = initiated_event_id
        self._started_event_id = started_event_id
        self._retry_state = retry_state

    @property
    def namespace(self) -> str:
        """Namespace for this error."""
        return self._namespace

    @property
    def workflow_id(self) -> str:
        """Workflow ID for this error."""
        return self._workflow_id

    @property
    def run_id(self) -> str:
        """Run ID for this error."""
        return self._run_id

    @property
    def workflow_type(self) -> str:
        """Workflow type for this error."""
        return self._workflow_type

    @property
    def initiated_event_id(self) -> int:
        """Initiated event ID for this error."""
        return self._initiated_event_id

    @property
    def started_event_id(self) -> int:
        """Started event ID for this error."""
        return self._started_event_id

    @property
    def retry_state(self) -> Optional[RetryState]:
        """Retry state for this error."""
        return self._retry_state


def is_cancelled_exception(exception: BaseException) -> bool:
    """Check whether the given exception is considered a cancellation exception
    according to Temporal.

    This is often used in a conditional of a catch clause to check whether a
    cancel occurred inside of a workflow. This can occur from
    :py:class:`asyncio.CancelledError` or :py:class:`CancelledError` or either
    :py:class:`ActivityError` or :py:class:`ChildWorkflowError` if either of
    those latter two have a :py:class:`CancelledError` cause.

    Args:
        exception: Exception to check.

    Returns:
        True if a cancelled exception, false if not.
    """
    return (
        isinstance(exception, asyncio.CancelledError)
        or isinstance(exception, CancelledError)
        or (
            (
                isinstance(exception, ActivityError)
                or isinstance(exception, ChildWorkflowError)
            )
            and isinstance(exception.cause, CancelledError)
        )
    )

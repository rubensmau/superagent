import asyncio
import json
import logging
from typing import AsyncIterable

import segment.analytics as analytics
from agentops.langchain_callback_handler import AsyncLangchainCallbackHandler
from decouple import config
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.request import (
    Workflow as WorkflowRequest,
)
from app.models.request import (
    WorkflowInvoke as WorkflowInvokeRequest,
)
from app.models.request import (
    WorkflowStep as WorkflowStepRequest,
)
from app.models.response import Workflow as WorkflowResponse
from app.models.response import WorkflowList as WorkflowListResponse
from app.models.response import WorkflowStep as WorkflowStepResponse
from app.models.response import WorkflowStepList as WorkflowStepListResponse
from app.utils.analytics import track_agent_invocation
from app.utils.api import get_current_api_user, handle_exception
from app.utils.callbacks import (
    CostCalcAsyncHandler,
    CustomAsyncIteratorCallbackHandler,
    get_session_tracker_handler,
)
from app.utils.helpers import stream_dict_keys
from app.utils.llm import LLM_MAPPING
from app.utils.prisma import prisma
from app.workflows.base import WorkflowBase

SEGMENT_WRITE_KEY = config("SEGMENT_WRITE_KEY", None)

router = APIRouter()
logger = logging.getLogger(__name__)
analytics.write_key = SEGMENT_WRITE_KEY


@router.post(
    "/workflows",
    name="create",
    description="Create a new workflow",
    response_model=WorkflowResponse,
)
async def create(body: WorkflowRequest, api_user=Depends(get_current_api_user)):
    """Endpoint for creating a workflow"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Created Workflow")
        data = await prisma.workflow.create(
            {
                **body.dict(),
                "apiUserId": api_user.id,
            }
        )
        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)


@router.get(
    "/workflows",
    name="list",
    description="List all workflows",
    response_model=WorkflowListResponse,
)
async def list(api_user=Depends(get_current_api_user), skip: int = 0, take: int = 50):
    """Endpoint for listing all workflows"""
    try:
        import math

        data = await prisma.workflow.find_many(
            where={"apiUserId": api_user.id},
            order={"createdAt": "desc"},
            include={"steps": {"include": {"agent": True}}},
            skip=skip,
            take=take,
        )

        # Get the total count of agents
        total_count = await prisma.workflow.count(where={"apiUserId": api_user.id})

        # Calculate the total number of pages
        total_pages = math.ceil(total_count / take)

        for workflow in data:
            for step in workflow.steps:
                step.agent.metadata = json.dumps(step.agent.metadata)

        return {"success": True, "data": data, "total_pages": total_pages}
    except Exception as e:
        handle_exception(e)


@router.get(
    "/workflows/{workflow_id}",
    name="get",
    description="Get a single workflow",
    response_model=WorkflowResponse,
)
async def get(workflow_id: str, api_user=Depends(get_current_api_user)):
    """Endpoint for getting a single workflow"""
    try:
        data = await prisma.workflow.find_first(
            where={"id": workflow_id, "apiUserId": api_user.id},
            include={
                "steps": {"include": {"agent": True}},
                "workflowConfigs": True,
            },
        )

        for workflow_config in data.workflowConfigs:
            workflow_config.config = json.dumps(workflow_config.config)

        for step in data.steps:
            step.agent.metadata = json.dumps(step.agent.metadata)

        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)


@router.patch(
    "/workflows/{workflow_id}",
    name="update",
    description="Patch a workflow",
    response_model=WorkflowResponse,
)
async def workflow_update(
    workflow_id: str, body: WorkflowRequest, api_user=Depends(get_current_api_user)
):
    """Endpoint for patching a workflow"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Updated Workflow")
        data = await prisma.workflow.update(
            where={"id": workflow_id},
            data={
                **body.dict(exclude_unset=True),
                "apiUserId": api_user.id,
            },
        )
        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)


@router.delete(
    "/workflows/{workflow_id}",
    name="delete",
    description="Delete a specific workflow",
)
async def delete(workflow_id: str, api_user=Depends(get_current_api_user)):
    """Endpoint for deleting a specific workflow"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Deleted Workflow")
        await prisma.workflowstep.delete_many(where={"workflowId": workflow_id})
        await prisma.workflow.delete(where={"id": workflow_id})
        return {"success": True, "data": None}
    except Exception as e:
        handle_exception(e)


@router.post(
    "/workflows/{workflow_id}/invoke",
    name="invoke",
    description="Invoke a specific workflow",
)
async def invoke(
    workflow_id: str,
    body: WorkflowInvokeRequest,
    api_user=Depends(get_current_api_user),
):
    """Endpoint for invoking a specific workflow"""
    if SEGMENT_WRITE_KEY:
        analytics.track(api_user.id, "Invoked Workflow")

    workflow_data = await prisma.workflow.find_unique(
        where={"id": workflow_id},
        include={"steps": {"order_by": {"order": "asc"}}},
    )
    session_id = body.sessionId or ""
    session_id = f"wf_{workflow_id}_{session_id}"
    input = body.input
    enable_streaming = body.enableStreaming
    output_schemas = body.outputSchemas
    last_output_schema = body.outputSchema

    workflow_steps = []
    for idx, step in enumerate(workflow_data.steps):
        agent_data = await prisma.agent.find_unique_or_raise(
            where={"id": step.agentId},
            include={
                "llms": {"include": {"llm": True}},
                "datasources": {
                    "include": {"datasource": {"include": {"vectorDb": True}}}
                },
                "tools": {"include": {"tool": True}},
            },
        )
        output_schema = agent_data.outputSchema
        llm_model = LLM_MAPPING.get(agent_data.llmModel)
        metadata = agent_data.metadata or {}

        if not llm_model and metadata.get("model"):
            llm_model = agent_data.metadata.get("model")

        if output_schemas.get(step.id):
            output_schema = output_schemas[step.id]
        elif last_output_schema and idx == len(workflow_data.steps) - 1:
            output_schema = last_output_schema

        item = {
            "callbacks": {
                "cost_calc": CostCalcAsyncHandler(model=llm_model),
            },
            "agent_name": agent_data.name,
            "output_schema": output_schema,
            "agent_data": agent_data,
        }
        session_tracker_handler = get_session_tracker_handler(
            workflow_data.id, agent_data.id, session_id, api_user.id
        )

        if session_tracker_handler:
            item["callbacks"]["session_tracker"] = session_tracker_handler

        if enable_streaming:
            item["callbacks"]["streaming"] = CustomAsyncIteratorCallbackHandler()

        workflow_steps.append(item)
    workflow_callbacks = []

    for s in workflow_steps:
        callbacks = []
        for _, v in s["callbacks"].items():
            callbacks.append(v)
        workflow_callbacks.append(callbacks)

    agentops_api_key = config("AGENTOPS_API_KEY", default=None)
    agentops_org_key = config("AGENTOPS_ORG_KEY", default=None)

    agentops_handler = AsyncLangchainCallbackHandler(
        api_key=agentops_api_key, org_key=agentops_org_key, tags=[session_id]
    )

    workflow = WorkflowBase(
        workflow_steps=workflow_steps,
        enable_streaming=enable_streaming,
        callbacks=workflow_callbacks,
        constructor_callbacks=[agentops_handler],
        session_id=session_id,
    )

    def track_invocation(output):
        for index, workflow_step in enumerate(workflow_steps):
            workflow_step_result = output.get("steps")[index]
            cost_callback = workflow_step["callbacks"]["cost_calc"]
            agent = workflow_steps[index]["agent_data"]

            track_agent_invocation(
                {
                    "workflow_id": workflow_id,
                    "agent": agent,
                    "user_id": api_user.id,
                    "session_id": session_id,
                    **workflow_step_result,
                    **vars(cost_callback),
                }
            )

    if enable_streaming:
        logger.info("Streaming enabled. Preparing streaming response...")

        async def send_message() -> AsyncIterable[str]:
            try:
                task = asyncio.ensure_future(workflow.arun(input))
                for workflow_step in workflow_steps:
                    output_schema = workflow_step["output_schema"]

                    # we are not streaming token by token if output schema is set
                    schema_tokens = ""

                    async for token in workflow_step["callbacks"]["streaming"].aiter():
                        if not output_schema:
                            agent_name = workflow_step["agent_name"]
                            async for val in stream_dict_keys(
                                {
                                    "id": agent_name,
                                    "data": token,
                                }
                            ):
                                yield val
                        else:
                            schema_tokens += token

                    if output_schema:
                        from langchain.output_parsers.json import SimpleJsonOutputParser

                        parser = SimpleJsonOutputParser()
                        try:
                            parsed_res = parser.parse(schema_tokens)
                        except Exception as e:
                            # TODO: stream schema parsing error as well
                            logger.error(f"Error in parsing schema: {e}")
                            parsed_res = {}

                        # stream line by line to prevent streaming large data in one go
                        for line in json.dumps(parsed_res).split("\n"):
                            agent_name = workflow_step["agent_name"]
                            async for val in stream_dict_keys(
                                {
                                    "id": agent_name,
                                    "data": line,
                                }
                            ):
                                yield val

                await task
                exception = task.exception()
                if exception:
                    raise exception

                workflow_result = task.result()

                for index, workflow_step in enumerate(workflow_steps):
                    workflow_step_result = workflow_result.get("steps")[index]

                    if SEGMENT_WRITE_KEY:
                        track_invocation(workflow_result)

                    for step in workflow_step_result.get("intermediate_steps", []):
                        (agent_action_message_log, tool_response) = step
                        function = agent_action_message_log.tool
                        args = agent_action_message_log.tool_input
                        if function and args:
                            async for val in stream_dict_keys(
                                {
                                    "event": "function_call",
                                    "data": {
                                        "step_name": workflow_step["agent_name"],
                                        "function": function,
                                        "args": json.dumps(args),
                                        "response": tool_response,
                                    },
                                }
                            ):
                                yield val

            except Exception as error:
                yield (f"event: error\n" f"data: {error}\n\n")

                if SEGMENT_WRITE_KEY:
                    for workflow_step in workflow_steps:
                        agent = workflow_step["agent_data"]
                        track_agent_invocation(
                            {
                                "workflow_id": workflow_id,
                                "agent": agent,
                                "user_id": api_user.id,
                                "session_id": session_id,
                                "error": str(error),
                                "status_code": 500,
                            }
                        )

                logger.exception(f"Error in send_message: {error}")
            finally:
                for workflow_step in workflow_steps:
                    workflow_step["callbacks"]["streaming"].done.set()

        generator = send_message()
        return StreamingResponse(generator, media_type="text/event-stream")

    logger.info("Streaming not enabled. Invoking workflow synchronously...")
    output = await workflow.arun(
        input,
    )

    if SEGMENT_WRITE_KEY:
        track_invocation(output)

    # End session
    agentops_handler.ao_client.end_session(
        "Success", end_state_reason="Workflow completed"
    )
    return {"success": True, "data": output}


# Workflow steps
@router.post(
    "/workflows/{workflow_id}/steps",
    name="add_step",
    description="Create a new workflow step",
    response_model=WorkflowStepResponse,
)
async def add_step(
    workflow_id: str, body: WorkflowStepRequest, api_user=Depends(get_current_api_user)
):
    """Endpoint for creating a workflow step"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Created Workflow Step")
        data = await prisma.workflowstep.create(
            {
                **body.dict(),
                "workflowId": workflow_id,
            },
            include={"agent": True, "workflow": True},
        )
        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)


@router.get(
    "/workflows/{workflow_id}/steps",
    name="list_steps",
    description="List all steps of a workflow",
    response_model=WorkflowStepListResponse,
)
async def list_steps(workflow_id: str, api_user=Depends(get_current_api_user)):
    """Endpoint for listing all steps of a workflow"""
    try:
        data = await prisma.workflowstep.find_many(
            where={"workflowId": workflow_id},
            order={"order": "asc"},
            include={"agent": True},
        )

        for step in data:
            step.agent.metadata = json.dumps(step.agent.metadata)

        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)


@router.delete(
    "/workflows/{workflow_id}/steps/{step_id}",
    name="delete_step",
    description="Delete a specific workflow step",
)
async def delete_step(
    workflow_id: str, step_id: str, api_user=Depends(get_current_api_user)
):
    """Endpoint for deleting a specific workflow step"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Deleted Workflow Step")
        await prisma.workflowstep.delete(where={"id": step_id})
        return {"success": True, "data": None}
    except Exception as e:
        handle_exception(e)


@router.patch(
    "/workflows/{workflow_id}/steps/{step_id}",
    name="update",
    description="Patch a workflow step",
    response_model=WorkflowStepResponse,
)
async def workflow_step_update(
    workflow_id: str,
    step_id: str,
    body: WorkflowStepRequest,
    api_user=Depends(get_current_api_user),
):
    """Endpoint for patching a workflow step"""
    try:
        if SEGMENT_WRITE_KEY:
            analytics.track(api_user.id, "Updated Workflow Step")

        data = await prisma.workflowstep.update(
            where={"id": step_id},
            data={
                **body.dict(exclude_unset=True),
                "workflowId": workflow_id,
            },
        )

        return {"success": True, "data": data}
    except Exception as e:
        handle_exception(e)

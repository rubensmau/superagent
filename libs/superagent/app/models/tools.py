from typing import Optional

from pydantic import BaseModel, Field


class AlgoliaInput(BaseModel):
    search_query: str
    num_of_results: int


class DatasourceInput(BaseModel):
    question: str


class SuperRagInput(BaseModel):
    question: str


class BingSearchInput(BaseModel):
    search_query: str


class CodeInterpreterInput(BaseModel):
    python_code: str


class MetaphorSearchInput(BaseModel):
    search_query: str


class PubMedInput(BaseModel):
    search_query: str


class ZapierInput(BaseModel):
    input: str


class OpenapiInput(BaseModel):
    input: str


class ChatGPTInput(BaseModel):
    input: str


class ReplicateInput(BaseModel):
    prompt: str


class AgentInput(BaseModel):
    input: str


class WolframInput(BaseModel):
    input: str


class E2BCodeExecutorInput(BaseModel):
    python_code: str


class BrowserInput(BaseModel):
    url: str = Field(..., description="A valid url including protocol to analyze")


class GPTVisionInputModel(BaseModel):
    query: str
    image_url: str


class GPTVisionInput(BaseModel):
    input: GPTVisionInputModel


class TTS1InputModel(BaseModel):
    text: str
    voice: str


class TTS1Input(BaseModel):
    input: TTS1InputModel


class HandOffInput(BaseModel):
    reason: str


class FunctionInput(BaseModel):
    config: dict


class HTTPInput(BaseModel):
    body: Optional[dict] = {}


class TavilyInput(BaseModel):
    query: str


class ScraperInput(BaseModel):
    url: str


class AdvancedScraperInput(BaseModel):
    url: str


class GoogleSearchInput(BaseModel):
    query: str


class SECInput(BaseModel):
    ticker: str = Field(..., description="The stock ticker symbol for the company")

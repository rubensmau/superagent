export class Api {
  private apiKey?: string

  constructor(apiKey?: string) {
    this.apiKey = apiKey
  }

  async fetchFromApi(
    endpoint: string,
    options: RequestInit = {},
    searchParams: Record<string, any> = {}
  ) {
    const url = new URL(
      `${process.env.NEXT_PUBLIC_SUPERAGENT_API_URL}${endpoint}`
    )

    Object.entries(searchParams).forEach(([key, value]) => {
      url.searchParams.append(key, value)
    })

    const response = await fetch(url.toString(), {
      ...options,
      headers: {
        "Content-Type": "application/json",
        authorization: `Bearer ${this.apiKey}`,
        ...options.headers,
      },
    })

    return await response.json()
  }

  async indentifyUser(payload: any) {
    return this.fetchFromApi("/api-users/identify", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async createAgent(payload: any) {
    return this.fetchFromApi("/agents", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async createAgentLLM(agentId: string, llmId: string) {
    return this.fetchFromApi(`/agents/${agentId}/llms`, {
      method: "POST",
      body: JSON.stringify({ llmId }),
    })
  }

  async createAgentTool(agentId: string, toolId: string) {
    return this.fetchFromApi(`/agents/${agentId}/tools`, {
      method: "POST",
      body: JSON.stringify({ toolId }),
    })
  }

  async createApiUser(payload: any) {
    return this.fetchFromApi("/api-users", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async createApiKey(payload: any) {
    return this.fetchFromApi("/api-keys", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async getApiKeys() {
    return this.fetchFromApi("/api-keys")
  }

  async updateApiKey(id: string, payload: any) {
    return this.fetchFromApi(`/api-keys/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async deleteApiKey(id: string) {
    return this.fetchFromApi(`/api-keys/${id}`, { method: "DELETE" })
  }

  async createDatasource(payload: any) {
    return this.fetchFromApi("/datasources", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async createAgentDatasource(agentId: string, datasourceId: string) {
    return this.fetchFromApi(`/agents/${agentId}/datasources`, {
      method: "POST",
      body: JSON.stringify({ datasourceId }),
    })
  }

  async createLLM(payload: any) {
    return this.fetchFromApi("/llms", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async createTool(payload: any) {
    return this.fetchFromApi("/tools", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async deleteAgentLLM(agentId: string, llmId: string) {
    return this.fetchFromApi(`/agents/${agentId}/llms/${llmId}`, {
      method: "DELETE",
    })
  }

  async deleteAgentById(id: string) {
    return this.fetchFromApi(`/agents/${id}`, { method: "DELETE" })
  }

  async deleteAgentTool(id: string, toolId: string) {
    return this.fetchFromApi(`/agents/${id}/tools/${toolId}`, {
      method: "DELETE",
    })
  }

  async deleteAgentDatasource(id: string, datasourceId: string) {
    return this.fetchFromApi(`/agents/${id}/datasources/${datasourceId}`, {
      method: "DELETE",
    })
  }

  async deleteDatasource(id: string) {
    return this.fetchFromApi(`/datasources/${id}`, { method: "DELETE" })
  }

  async deleteTool(id: string) {
    return this.fetchFromApi(`/tools/${id}`, { method: "DELETE" })
  }

  async getAgents(
    searchParams: { take?: number; skip?: number } = { skip: 0, take: 300 }
  ) {
    return this.fetchFromApi("/agents", {}, searchParams)
  }

  async getAgentById(id: string) {
    return this.fetchFromApi(`/agents/${id}`)
  }

  async getAgentRuns(id: string) {
    return this.fetchFromApi(`/agents/${id}/runs`)
  }

  async getDatasources(
    searchParams: { take?: number; skip?: number } = { skip: 0, take: 50 }
  ) {
    return this.fetchFromApi(`/datasources`, {}, searchParams)
  }

  async getLLMs() {
    return this.fetchFromApi(`/llms`)
  }

  async getTools(
    searchParams: { take?: number; skip?: number } = { skip: 0, take: 50 }
  ) {
    return this.fetchFromApi("/tools", {}, searchParams)
  }

  async getRuns(searchParams?: {
    workflow_id?: string
    agent_id?: string
    limit?: number
    from_page?: number
    to_page?: number
  }) {
    return this.fetchFromApi("/runs", {}, searchParams)
  }

  async patchAgent(id: string, payload: any) {
    return this.fetchFromApi(`/agents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async patchDatasource(id: string, payload: any) {
    return this.fetchFromApi(`/datasources/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async patchLLM(id: string, payload: any) {
    return this.fetchFromApi(`/llms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async patchTool(id: string, payload: any) {
    return this.fetchFromApi(`/tools/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async getWorkflows(
    searchParams: { take?: number; skip?: number } = { skip: 0, take: 50 }
  ) {
    return this.fetchFromApi("/workflows", {}, searchParams)
  }

  async getWorkflowById(id: string) {
    return this.fetchFromApi(`/workflows/${id}`)
  }

  async createWorkflow(payload: any) {
    return this.fetchFromApi("/workflows", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async generateWorkflow(workflowId: string, payload: any) {
    // TODO: update fetchFromApi and use it
    return fetch(
      `${process.env.NEXT_PUBLIC_SUPERAGENT_API_URL}/workflows/${workflowId}/config`,
      {
        method: "POST",
        body: payload,
        headers: {
          "Content-Type": "application/x-yaml",
          authorization: `Bearer ${this.apiKey}`,
        },
      }
    )
  }

  async getWorkflowSteps(id: string) {
    return this.fetchFromApi(`/workflows/${id}/steps`)
  }

  async createWorkflowStep(workflowId: string, payload: any) {
    return this.fetchFromApi(`/workflows/${workflowId}/steps`, {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async patchWorkflowStep(workflowId: string, stepId: string, payload: any) {
    return this.fetchFromApi(`/workflows/${workflowId}/steps/${stepId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async deleteWorkflowStep(workflowId: string, stepId: string) {
    return this.fetchFromApi(`/workflows/${workflowId}/steps/${stepId}`, {
      method: "DELETE",
    })
  }

  async patchWorkflow(workflowId: string, payload: any) {
    return this.fetchFromApi(`/workflows/${workflowId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async deleteWorkflow(workflowId: string) {
    return this.fetchFromApi(`/workflows/${workflowId}`, {
      method: "DELETE",
    })
  }

  async getVectorDbs() {
    return this.fetchFromApi(`/vector-dbs`)
  }

  async createVectorDb(payload: any) {
    return this.fetchFromApi("/vector-db", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  }

  async patchVectorDb(id: string, payload: any) {
    return this.fetchFromApi(`/vector-dbs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async deleteVectorDb(id: string) {
    return this.fetchFromApi(`/vector-dbs/${id}`, {
      method: "DELETE",
    })
  }
}

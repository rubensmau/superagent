import { cookies } from "next/headers"
import { createServerComponentClient } from "@supabase/auth-helpers-nextjs"

import { Api } from "@/lib/api"

import { columns } from "./columns"
import { DataTable } from "./data-table"
import Header from "./header"

export const dynamic = "force-dynamic"

export default async function Agents({
  searchParams,
}: {
  searchParams: {
    page: string
    take: string
  }
}) {
  const supabase = createServerComponentClient({ cookies })
  const {
    data: { user },
  } = await supabase.auth.getUser()
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("user_id", user?.id)
    .single()
  const api = new Api(profile.api_key)
  const { take: takeStr, page: pageStr } = searchParams
  const take = Number(takeStr) || 10,
    page = Number(pageStr) || 1

  const { data: agents, total_pages } = await api.getAgents({
    skip: (page - 1) * take,
    take,
  })

  return (
    <div className="flex flex-col space-y-8">
      <Header profile={profile} />
      <DataTable
        columns={columns}
        data={agents || []}
        profile={profile}
        pagination={{
          take,
          currentPageNumber: page,
          totalPages: total_pages,
        }}
      />
    </div>
  )
}

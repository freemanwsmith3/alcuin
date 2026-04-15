import { ChatApp } from "@/components/chat/chat-app"

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ company: string }>
}) {
  const { company } = await params
  const displayName = company.charAt(0).toUpperCase() + company.slice(1)

  return <ChatApp company={displayName} />
}

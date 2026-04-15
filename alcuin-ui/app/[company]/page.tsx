import type { Metadata } from "next"
import { ChatApp } from "@/components/chat/chat-app"

function slugToName(slug: string): string {
  return slug
    .split("-")
    .map((word) => word === "and" ? "&" : word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ company: string }>
}): Promise<Metadata> {
  const { company } = await params
  return { title: `${slugToName(company)} - AI Chat` }
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ company: string }>
}) {
  const { company } = await params
  return <ChatApp company={slugToName(company)} />
}

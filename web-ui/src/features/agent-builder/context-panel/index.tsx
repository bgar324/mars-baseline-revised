"use client"

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { useSelectedPersona } from "@/hooks/use-selected-persona"

import { ContextPanelHeader } from "./header"
import { Profile } from "./profile"
import { References } from "./references"

const TAB_TRIGGER =
  "flex-none px-3 data-active:text-primary data-active:after:bg-primary"

export function ContextPanel() {
  const persona = useSelectedPersona()

  if (!persona) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-s text-center text-muted-foreground">
          Select a researcher
          <br />
          to view details.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-full min-w-0 flex-col overflow-hidden">
      <ContextPanelHeader persona={persona} />
      <Tabs
        defaultValue="profile"
        className="flex min-h-0 flex-1 flex-col gap-0"
      >
        <TabsList variant="line" className="mx-4 mt-2 w-auto justify-start">
          <TabsTrigger value="profile" className={TAB_TRIGGER}>
            Profile
          </TabsTrigger>
          <TabsTrigger value="references" className={TAB_TRIGGER}>
            References
          </TabsTrigger>
        </TabsList>
        <TabsContent
          value="profile"
          className="min-h-0 flex-1 overflow-y-auto px-4 pt-6 pb-4"
        >
          <Profile persona={persona} />
        </TabsContent>
        <TabsContent
          value="references"
          className="min-h-0 flex-1 overflow-y-auto px-4 pt-6 pb-4"
        >
          <References persona={persona} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

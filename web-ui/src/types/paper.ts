import { z } from "zod"

export const AuthorSchema = z.object({
  id: z.string().nullable().optional(),
  name: z.string(),
})

export const PaperSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    abstract: z.string().nullable().optional(),
    tldr: z.string().nullable().optional(),
    venue: z.string().nullable().optional(),
    year: z.number().int().nullable().optional(),
    url: z.string().nullable().optional(),
    doi: z.string().nullable().optional(),
    citation_count: z.number().int().nullable().optional(),
    influential_citation_count: z.number().int().nullable().optional(),
    authors: z.array(AuthorSchema).default([]),
  })
  .passthrough()

export const PaperListSchema = z.array(PaperSchema)

export type Author = z.infer<typeof AuthorSchema>
export type Paper = z.infer<typeof PaperSchema>

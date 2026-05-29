export function initials(name: string): string {
  const field = name.split("·")[0].trim()
  const parts = field.split(/\s+/).filter((p) => /[\p{L}\p{N}]/u.test(p))
  if (parts.length === 0) return "?"
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

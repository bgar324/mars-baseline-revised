import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default:
          "border border-primary/35 bg-linear-to-b from-primary/85 to-primary text-primary-foreground duration-150 ease-out will-change-transform hover:brightness-110 active:scale-[0.97] active:brightness-95 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.2),0_1px_3px_0_rgba(0,0,0,0.15)] dark:border-primary/20 dark:bg-linear-to-t dark:from-primary/75",
        shine:
          "border border-primary/35 bg-linear-to-b from-primary/85 to-primary text-primary-foreground duration-150 ease-out will-change-transform hover:brightness-110 active:scale-[0.97] active:brightness-95 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.2),0_1px_3px_0_rgba(0,0,0,0.15)] dark:border-primary/20 dark:bg-linear-to-t dark:from-primary/75",
        destructive:
          "border border-destructive/35 bg-linear-to-b from-destructive/85 to-destructive text-white duration-150 ease-out will-change-transform hover:brightness-110 active:scale-[0.97] active:brightness-95 focus-visible:ring-destructive/20 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.2),0_1px_3px_0_rgba(0,0,0,0.15)] dark:border-destructive/20 dark:bg-linear-to-t dark:from-destructive/75 dark:focus-visible:ring-destructive/40",
        "destructive-shine":
          "border border-destructive/35 bg-linear-to-b from-destructive/85 to-destructive text-white duration-150 ease-out will-change-transform hover:brightness-110 active:scale-[0.97] active:brightness-95 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.2),0_1px_3px_0_rgba(0,0,0,0.15)] dark:border-destructive/20 dark:bg-linear-to-t dark:from-destructive/75",
        outline:
          "border border-border/90 bg-linear-to-b from-background to-muted/55 text-foreground duration-150 ease-out will-change-transform hover:brightness-105 active:scale-[0.97] active:brightness-95 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.65),0_1px_3px_0_rgba(0,0,0,0.13)] dark:border-input dark:from-input/45 dark:to-input/80 dark:[box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.08),0_1px_3px_0_rgba(0,0,0,0.3)]",
        secondary:
          "border border-border/80 bg-linear-to-b from-secondary/75 to-secondary text-secondary-foreground duration-150 ease-out will-change-transform hover:brightness-105 active:scale-[0.97] active:brightness-95 [box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.5),0_1px_3px_0_rgba(0,0,0,0.13)] dark:[box-shadow:inset_0_1px_0_0_rgba(255,255,255,0.08),0_1px_3px_0_rgba(0,0,0,0.3)]",
        ghost:
          "hover:bg-muted active:scale-[0.94] dark:hover:bg-muted/50",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        xs: "h-6 gap-1 rounded-md px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-xs": "size-6 rounded-md [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }

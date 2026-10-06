import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ComponentProps<"button"> & {
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "default" | "sm" | "lg" | "icon";
};

export function Button({
  className,
  variant = "primary",
  size = "default",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-40",
        variant === "primary" &&
          "gradient-accent text-accent-foreground shadow-soft hover:brightness-105 active:brightness-95",
        variant === "secondary" &&
          "bg-secondary text-secondary-foreground hover:bg-muted",
        variant === "outline" &&
          "border border-border bg-transparent text-foreground hover:border-accent/60 hover:bg-surface",
        variant === "ghost" &&
          "text-muted-foreground hover:bg-surface hover:text-foreground",
        size === "default" && "h-11 px-5",
        size === "sm" && "h-9 px-4 text-[0.8rem]",
        size === "lg" && "h-12 px-7 text-[0.95rem]",
        size === "icon" && "size-10 shrink-0 p-0",
        className,
      )}
      {...props}
    />
  );
}

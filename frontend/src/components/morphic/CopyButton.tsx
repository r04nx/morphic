import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export function CopyButton({
  value,
  label,
  className,
}: {
  value: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async (e) => {
        e.preventDefault();
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          toast.success(`${label ?? "Copied"} to clipboard`);
          setTimeout(() => setCopied(false), 1400);
        } catch {
          toast.error("Copy failed");
        }
      }}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-border bg-secondary/60 px-1.5 py-0.5 font-mono text-xs text-muted-foreground transition hover:border-primary/40 hover:text-foreground",
        className,
      )}
    >
      {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
      {label ?? "Copy"}
    </button>
  );
}
